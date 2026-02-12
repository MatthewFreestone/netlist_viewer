from src.netlist_viewer.layout import PlacedNet, add_spring_locations, to_nx_graph, Point
from src.netlist_viewer.gui import main
from src.netlist_viewer.spice_parser import SpiceParser
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

if __name__ == "__main__":
    netlist = """
    R1 1 2 1k
    R2 2 3 1k
    R3 3 0 1k
    C1 2 0 10u
    C2 2 0 10u
    C3 2 0 10u
    V1 1 0 DC 5""".splitlines()
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    fig, ax = plt.subplots()
    x = [i.location.x for i in placed.instances]
    y = [i.location.y for i in placed.instances]
    ax.scatter(x, y)
    for inst in placed.instances:
        ax.text(inst.location.x, inst.location.y, inst.instance.name)
    for edge in placed.edges:
        start = placed.get_node(edge[0]).location
        end = placed.get_node(edge[1]).location
        ax.plot((start.x, end.x), (start.y, end.y))
    plt.show()
    
    # nodes = [v for k,v in pos.items() if type(k) is int]

    # fig, ax = plt.subplots()
    # for node in pos:
    # ax.plot()
    # plt.subplots()    
    # nx.draw(G, with_labels=True, font_weight='bold')
    # plt.show()