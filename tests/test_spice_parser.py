import pytest
from src.netlist_viewer.spice_parser import Primitive, SpiceParser, SpiceFormatError

def test_parse_resistor():
    netlist = ["R1 1 0 10k param=10f"]
    parser = SpiceParser()
    components = parser.parse(netlist)
    
    assert len(components) == 1
    assert components[0].name == "R1" 
    assert components[0].primitive == Primitive.RES
    assert components[0].nets == ["1", "0"]
    assert components[0].parameters.keyed == [('param', '10f')]
    assert components[0].parameters.unkeyed == ["10k"]

def test_parse_invalid_syntax():
    with pytest.raises(SpiceFormatError):
        parser = SpiceParser()
        parser.parse("INVALID LINE")


@pytest.fixture
def sample_circuit() -> list[str]:
    """Reusable test data"""
    return """
    R1 1 2 1k
    C1 2 0 10u
    V1 1 0 DC 5
    """.splitlines()

def test_full_circuit(sample_circuit):
    parser = SpiceParser()
    components = parser.parse(sample_circuit)
    assert len(components) == 3
    assert components[0].primitive == Primitive.RES
    assert components[1].primitive == Primitive.CAP
    assert components[2].primitive == Primitive.VSOURCE