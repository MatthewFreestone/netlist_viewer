from collections import defaultdict, namedtuple
from dataclasses import dataclass
import logging
import time
import networkx as nx

from src.netlist_viewer.spice_parser import Instance, Netlist

net_indicator = "$NET$"
def to_nx_graph(netlist: Netlist) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(0, len(netlist.instances)))

    # we want an adj list where we see what nodes are connected to what nets.
    # if there are only 2, we'll add an edge. Otherwise, we need a node.

    adj_list = defaultdict(list)
    for index, inst in enumerate(netlist.instances):
        for net in inst.nets:
            adj_list[net].append(index)

    for net, nodes in adj_list.items():
        # if len(nodes) == 1:
        #     continue
        if len(nodes) == 2:
            start, end = nodes
            G.add_edge(start, end, weight=2, useful=True)
        else:
            net_name = net_indicator + str(net)
            G.add_node(net_name)
            for n in nodes:
                G.add_edge(net_name, n, weight=1, useful=True)
                for o_n in nodes:
                    if n != o_n:
                        # a hint to the spring layout to keep 
                        # nodes on the same net closer
                        G.add_edge(n, o_n, weight=0.5, useful=False)
    return G

Point = namedtuple("Point", "x y")

@dataclass
class PlacedInstance:
    instance: Instance 
    location: Point

@dataclass 
class PlacedNet:
    name: str
    location: Point



@dataclass
class PlacedNetlist:
    source: Netlist
    instances: list[PlacedInstance]
    net_nodes: dict[str, PlacedNet]
    edges: list[tuple[int | str, int | str]]

    def get_node(self, key: int | str) -> PlacedInstance | PlacedNet:
        if type(key) is int:
            return self.instances[key]
        elif type(key) is str:
            return self.net_nodes[key]
        else:
            raise IndexError("Bad index")


def add_spring_locations(netlist: Netlist) -> PlacedNetlist:
    graph_rep = to_nx_graph(netlist)
    start_time = time.time()
    if nx.is_planar(graph_rep):
        logging.info("Graph was planar")
        pos = nx.planar_layout(graph_rep)
    else:
        logging.info("Graph was not planar")
        pos = nx.spring_layout(graph_rep, method="energy", seed=0)
    end_time = time.time()
    logging.info("Calculated layout in %f s", end_time-start_time)
    placed_insts: list[PlacedInstance] = []
    net_nodes: dict[str, PlacedNet] = {}
    for node_id, loc in pos.items():
        x,y = loc
        if type(node_id) is int:
            current_inst = netlist.instances[node_id]
            i = PlacedInstance(current_inst, Point(x, y))
            placed_insts.append(i)
        else:
            net_nodes[node_id] = PlacedNet(node_id, Point(x, y))
    
    edges = [(e[0],e[1]) for e in graph_rep.edges.data() if e[2].get('useful', False)]
    return PlacedNetlist(netlist, placed_insts, net_nodes, edges)

    