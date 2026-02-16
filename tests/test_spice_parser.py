from typing import LiteralString
import pytest
from src.netlist_viewer.layout import NetlistGraph
from src.netlist_viewer.spice_parser import Primitive, SpiceParser, SpiceFormatError


def test_parse_resistor():
    netlist = ["R1 1 0 10k param=10f"]
    parser = SpiceParser()
    components = parser.parse(netlist).instances

    assert len(components) == 1
    assert components[0].name == "R1"
    assert components[0].primitive == Primitive.RES
    assert components[0].nets == ["1", "0"]
    assert components[0].parameters.keyed == [("param", "10f")]
    assert components[0].parameters.unkeyed == ["10k"]


def test_parse_invalid_syntax():
    with pytest.raises(SpiceFormatError):
        parser = SpiceParser()
        parser.parse("INVALID LINE")


@pytest.fixture
def sample_circuit() -> list[LiteralString]:
    """Reusable test data"""
    return """
    R1 1 2 1k
    C1 2 0 10u
    C2 2 0 10u
    V1 1 0 DC 5
    """.splitlines()


def test_full_circuit(sample_circuit):
    parser = SpiceParser()
    components = parser.parse(sample_circuit).instances
    assert len(components) == 4
    assert components[0].primitive == Primitive.RES
    assert components[1].primitive == Primitive.CAP
    assert components[2].primitive == Primitive.CAP
    assert components[3].primitive == Primitive.VSOURCE


def test_nx(sample_circuit):
    parser = SpiceParser()
    components = parser.parse(sample_circuit)
    g = NetlistGraph.from_netlist(components)
    assert len(g.nodes) == 6  # 4 inst, net 2, net 0 split up split up
    assert len(g.edges) == 7  # R1V1, R1-2, C1-2, C1-0, C2-0, C2-2, V1-0
