from __future__ import annotations
from collections import defaultdict
from typing import TypeGuard
from dataclasses import dataclass
import logging
import time
import networkx as nx

from src.netlist_viewer.spice_parser import Instance, Netlist

NET_INDICATOR = "$NET$"

# nodes added to a net are str, actual instances are int
type NodeReference = str | int


@dataclass
class NetlistGraph:
    """An representation of a netlist graph; allows identical edges on different nets"""

    @dataclass
    class TopologyEdge:
        start: NodeReference
        end: NodeReference
        weight: float
        net: str

    @dataclass
    class WeightHintEdge:
        """An edge which only exists to assist spring layout"""

        start: NodeReference
        end: NodeReference
        weight: float

    nodes: list[NodeReference]
    edges: list[TopologyEdge]
    spring_hint_edges: list[WeightHintEdge]

    def from_netlist(netlist: Netlist) -> NetlistGraph:
        final_nodes: list[NodeReference] = [i for i in range(len(netlist.instances))]
        final_edges: list[NetlistGraph.TopologyEdge] = []
        final_hint_edges: list[NetlistGraph.WeightHintEdge] = []

        adj_list: defaultdict[str, list[int]] = defaultdict(list)
        for index, inst in enumerate(netlist.instances):
            for net in inst.nets:
                adj_list[net].append(index)
        for net, nodes in adj_list.items():
            if len(nodes) == 1:
                logging.warning(
                    "Floating net %s only connected to node %d", net, nodes[0]
                )
            elif len(nodes) == 2:
                start, end = nodes
                logging.debug("Add edge (%d,%d) on net '%s'", start, end, net)
                e = NetlistGraph.TopologyEdge(start, end, weight=2, net=net)
                final_edges.append(e)
            else:
                net_name = NET_INDICATOR + str(net)
                final_nodes.append(net_name)
                for n in nodes:
                    e = NetlistGraph.TopologyEdge(net_name, n, weight=1, net=net)
                    final_edges.append(e)
                    for o_n in nodes:
                        if n != o_n:
                            # a hint to the spring layout to keep
                            # nodes on the same net closer
                            e = NetlistGraph.WeightHintEdge(net_name, n, weight=0.5)
                            final_hint_edges.append(e)
        return NetlistGraph(final_nodes, final_edges, final_hint_edges)

    def to_nx_graph(self, include_hints=False) -> nx.Graph:
        g = nx.Graph()
        g.add_nodes_from(self.nodes)
        g.add_edges_from(
            (e.start, e.end, dict(net=e.net, weight=e.weight)) for e in self.edges
        )
        if include_hints:
            g.add_edges_from(
                (e.start, e.end, dict(weight=e.weight)) for e in self.spring_hint_edges
            )
        return g


@dataclass
class Point:
    x: float
    y: float


@dataclass
class PlacedInstance:
    instance: Instance
    location: Point

    def get_name(self) -> str:
        return self.instance.name


@dataclass
class PlacedNet:
    name: str
    location: Point

    def get_name(self) -> str:
        return self.name


@dataclass
class Edge:
    start: NodeReference
    end: NodeReference
    net: str


@dataclass
class PlacedNetlist:
    source: Netlist
    instances: list[PlacedInstance]
    net_nodes: dict[str, PlacedNet]
    edges: list[Edge]

    def get_node(self, key: NodeReference) -> PlacedInstance | PlacedNet:
        if isinstance(key, int):
            return self.instances[key]
        elif isinstance(key, str):
            return self.net_nodes[key]
        else:
            raise IndexError("Bad index")


def _is_placed_list(
    items: list[PlacedInstance | None],
) -> TypeGuard[list[PlacedInstance]]:
    if not isinstance(items, list):
        return False
    return all(type(i) is PlacedInstance for i in items)


def add_spring_locations(netlist: Netlist) -> PlacedNetlist:
    """Use networkx to place netlist instances in a sensible location"""
    start_time = time.time()
    intermediate: NetlistGraph = NetlistGraph.from_netlist(netlist)
    no_hint_graph = intermediate.to_nx_graph(include_hints=False)
    if nx.is_planar(no_hint_graph):
        pos = nx.planar_layout(no_hint_graph)
    else:
        logging.info("Graph was not planar, using spring layout.")
        graph_rep = intermediate.to_nx_graph(include_hints=True)
        pos = nx.spring_layout(graph_rep, method="energy", seed=0)
        # TODO: Try out spectral_layout, kamada_kawai_layout
    end_time = time.time()
    logging.info("Calculated layout in %f s", end_time - start_time)
    # the nodes that come back tend to be out of order, but should still be 0 to n-1
    placed_insts: list[None | PlacedInstance] = [None] * len(netlist.instances)
    net_nodes: dict[str, PlacedNet] = {}
    for node_id, loc in pos.items():
        x, y = loc
        if isinstance(node_id, int):
            current_inst = netlist.instances[node_id]
            i = PlacedInstance(current_inst, Point(x, y))
            placed_insts[node_id] = i
        else:
            net_nodes[node_id] = PlacedNet(node_id, Point(x, y))
    edges = [Edge(e.start, e.end, e.net) for e in intermediate.edges]

    assert _is_placed_list(placed_insts)
    return PlacedNetlist(netlist, placed_insts, net_nodes, edges)
