from src.netlist_viewer.layout import to_nx_graph
from src.netlist_viewer.gui import main
from src.netlist_viewer.spice_parser import SpiceParser
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

if __name__ == "__main__":
    # main.main()

    netlist = """
    R1 1 2 1k
    C1 2 0 10u
    C2 2 0 10u
    V1 1 0 DC 5""".splitlines()
    parser = SpiceParser()
    components = parser.parse(netlist)
    G = to_nx_graph(components)
    pos = nx.spring_layout(G)
    nodes = np.array([v for k,v in pos.items()])
    fig, ax = plt.subplots()
    ax.scatter(nodes[:,0], nodes[:, 1])
    for edge in G.edges:
        start = pos[edge[0]]
        end = pos[edge[1]]
        ax.plot((start[0], end[0]), (start[1], end[1]))
    plt.show()
    
    # nodes = [v for k,v in pos.items() if type(k) is int]

    # fig, ax = plt.subplots()
    # for node in pos:
    # ax.plot()
    # plt.subplots()    
    # nx.draw(G, with_labels=True, font_weight='bold')
    # plt.show()