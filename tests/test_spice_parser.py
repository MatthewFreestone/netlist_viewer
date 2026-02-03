import pytest
from src.netlist_viewer.spice_parser import SpiceParser

def test_parse_resistor():
    netlist = ["R1 1 0 10k"]
    parser = SpiceParser()
    components = parser.parse(netlist)
    
    assert len(components) == 1
    assert components[0].name == "R1"
    assert components[0].nets == ["1", "0"]
    assert components[0].parameters == dict()
