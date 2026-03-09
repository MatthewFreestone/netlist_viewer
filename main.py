from netlist_viewer.layout import add_spring_locations
from netlist_viewer.routing import route_netlist
from netlist_viewer.gui.main import open_ui
from netlist_viewer.spice_parser import SpiceParser
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    netlist = """
    * Demo circuit with controlled sources
    V1 vcc 0 DC 5
    Vin input 0 AC 1

    * Input network
    R1 vcc input 10k
    C1 input 0 1u

    * Voltage-controlled voltage source (amplifier)
    E1 n2 0 vcc input 10

    * Voltage-controlled current source (transconductance)
    G1 n3 0 
       + input 0 1m
    R2 n3 0 1k

    * Current sensing and controlled sources
    Vsense n2 n4 DC 0
    F1 n4 0 Vsense 2
    H1 output 0 Vsense 1k

    * Output load
    R3 output 0 10k
    C2 output 0 10p
    """
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    routed = route_netlist(placed)
    open_ui(routed)
