from src.netlist_viewer.layout import add_spring_locations
from src.netlist_viewer.gui.main import main
from src.netlist_viewer.spice_parser import SpiceParser
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    netlist = """
    R1 1 2 1k
    R2 2 3 1k
    R3 3 0 1k
    C1 2 0 10u
    C2 2 0 10u
    V1 1 0 DC 5"""
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    main(placed)