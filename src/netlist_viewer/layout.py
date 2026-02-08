from collections import defaultdict
import networkx as nx

from src.netlist_viewer.spice_parser import Netlist

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
        if len(nodes) == 1:
            continue
        if len(nodes) == 2:
            start, end = nodes
            G.add_edge(start, end, )
        else:
            net_name="NET_" + str(net)
            G.add_node(net_name)
            for edge in nodes:
                G.add_edge(net_name, edge)
    return G
    # nx.spring_layout()