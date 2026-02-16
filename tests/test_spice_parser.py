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


def test_parse_inductor():
    parser = SpiceParser()
    components = parser.parse(["L1 in out 100u"]).instances

    assert len(components) == 1
    assert components[0].name == "L1"
    assert components[0].primitive == Primitive.IND
    assert components[0].nets == ["in", "out"]
    assert components[0].parameters.unkeyed == ["100u"]


def test_parse_diode():
    parser = SpiceParser()
    components = parser.parse(["D1 anode cathode D1N4148"]).instances

    assert len(components) == 1
    assert components[0].name == "D1"
    assert components[0].primitive == Primitive.DIODE
    assert components[0].nets == ["anode", "cathode"]
    assert components[0].parameters.unkeyed == ["D1N4148"]


def test_parse_bjt():
    parser = SpiceParser()
    components = parser.parse(["Q1 collector base emitter 2N2222"]).instances

    assert len(components) == 1
    assert components[0].name == "Q1"
    assert components[0].primitive == Primitive.BJT
    assert components[0].nets == ["collector", "base", "emitter"]
    assert components[0].parameters.unkeyed == ["2N2222"]


def test_parse_mosfet():
    parser = SpiceParser()
    components = parser.parse(["M1 drain gate source bulk NMOS W=10u L=1u"]).instances

    assert len(components) == 1
    assert components[0].name == "M1"
    assert components[0].primitive == Primitive.MOSFET
    assert components[0].nets == ["drain", "gate", "source", "bulk"]
    assert components[0].parameters.unkeyed == ["NMOS"]
    assert ("W", "10u") in components[0].parameters.keyed
    assert ("L", "1u") in components[0].parameters.keyed


def test_parse_jfet():
    parser = SpiceParser()
    components = parser.parse(["J1 drain gate source 2N5457"]).instances

    assert len(components) == 1
    assert components[0].name == "J1"
    assert components[0].primitive == Primitive.JFET
    assert components[0].nets == ["drain", "gate", "source"]
    assert components[0].parameters.unkeyed == ["2N5457"]


def test_mixed_circuit_with_new_primitives():
    """Test a circuit using multiple primitive types."""
    netlist = """
    V1 vcc 0 DC 12
    R1 vcc collector 1k
    Q1 collector base emitter 2N2222
    R2 base vcc 10k
    R3 emitter 0 100
    C1 base 0 10u
    L1 vcc filtered 100u
    D1 filtered 0 1N4001
    """.splitlines()

    parser = SpiceParser()
    components = parser.parse(netlist).instances

    assert len(components) == 8
    primitives = [c.primitive for c in components]
    assert primitives.count(Primitive.RES) == 3
    assert primitives.count(Primitive.CAP) == 1
    assert primitives.count(Primitive.IND) == 1
    assert primitives.count(Primitive.DIODE) == 1
    assert primitives.count(Primitive.BJT) == 1
    assert primitives.count(Primitive.VSOURCE) == 1
