from netlist_viewer.layout import add_spring_locations
from netlist_viewer.routing import route_netlist
from netlist_viewer.gui.main import open_ui
from netlist_viewer.spice_parser import SpiceParser
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    netlist = """
    * Wilson current mirror

    Vcc vcc 0 DC 10

    * Reference current (Iref = Vcc/Rref)
    Rref vcc ref 10k

    * Q1: reference transistor
    Q1 ref base q1e NPN

    * Q3: feedback transistor (improves output impedance)
    Q3 q1e ref 0 NPN

    * Q2: output transistor
    Q2 out base 0 NPN

    * Output load
    Rload vcc out 1k
    """
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    routed = route_netlist(placed)
    open_ui(routed)
