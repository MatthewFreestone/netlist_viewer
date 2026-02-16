from src.netlist_viewer.layout import add_spring_locations
from src.netlist_viewer.gui.main import main
from src.netlist_viewer.spice_parser import SpiceParser
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # netlist = """
    # R1 0 1 1k
    # V1 1 0 DC 5"""
    netlist = """
    V1 vcc 0 DC 12
    R1 vcc collector 1k
    Q1 collector base emitter 2N2222
    R2 base vcc 10k
    R3 emitter 0 100
    C1 base 0 10u
    L1 vcc filtered 100u
    D1 filtered 0 1N4001"""
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    main(placed)
