from netlist_viewer.layout import add_spring_locations
from netlist_viewer.gui.main import open_ui
from netlist_viewer.spice_parser import SpiceParser
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    netlist = """
    * Inverter subcircuit
    .SUBCKT inv in out VDD VSS
    M1 out in VDD VDD PMOS W=2u L=1u
    M2 out in VSS VSS NMOS W=1u L=1u
    .ENDS

    * Buffer subcircuit (two inverters)
    .SUBCKT buf in out VDD VSS
    X1 in mid VDD VSS inv
    X2 mid out VDD VSS inv
    .ENDS

    * 2-port subckt
    .SUBCKT res1 a b r=10k
    R1 a b r=r/2
    R2 a b r=r/2
    .ENDS

    * Top level circuit
    V1 vcc 0 DC 5
    X0 input vcc res1 r=10k

    X1 input n1 vcc 0 inv
    X2 n1 n2 vcc 0 inv
    X3 n2 output vcc 0 buf

    C1 output 0 10p
    """
    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)
    open_ui(placed)
