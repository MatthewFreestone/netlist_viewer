from typing import LiteralString
import pytest
from netlist_viewer.layout import NetlistGraph
from netlist_viewer.spice_parser import (
    Primitive,
    SpiceParser,
    SpiceFormatError,
)


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
    # 4 instances + 2 net nodes (net 2 and 0 have 3+ connections)
    assert len(g.nodes) == 6
    # Net 1: direct R1-V1 edge, Net 2: 3 edges to net node, Net 0: 3 edges to net node
    assert len(g.edges) == 7


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


def test_parse_subckt_definition():
    netlist = """
    .SUBCKT inv in out vdd vss
    M1 out in vdd vdd PMOS W=2u L=1u
    M2 out in vss vss NMOS W=1u L=1u
    .ENDS
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    assert "inv" in result.subckts
    subckt = result.subckts["inv"]
    assert subckt.name == "inv"
    assert subckt.ports == ["in", "out", "vdd", "vss"]
    assert len(subckt.instances) == 2
    assert subckt.instances[0].primitive == Primitive.MOSFET
    assert subckt.instances[1].primitive == Primitive.MOSFET


def test_parse_subckt_with_params():
    netlist = """
    .SUBCKT res2 a b W=1u L=10u
    R1 a mid 1k
    R2 mid b 1k
    .ENDS
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    subckt = result.subckts["res2"]
    assert subckt.ports == ["a", "b"]
    assert ("W", "1u") in subckt.parameters.keyed
    assert ("L", "10u") in subckt.parameters.keyed


def test_parse_subckt_instance():
    netlist = """
    .SUBCKT inv in out vdd vss
    M1 out in vdd vdd PMOS
    M2 out in vss vss NMOS
    .ENDS

    X1 input output VCC GND inv
    X2 output buffered VCC GND inv
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    assert len(result.instances) == 2
    assert result.instances[0].primitive == Primitive.SUBCKT
    assert result.instances[0].name == "X1"
    assert result.instances[0].subckt_name == "inv"
    assert result.instances[0].nets == ["input", "output", "VCC", "GND"]

    assert result.instances[1].name == "X2"
    assert result.instances[1].nets == ["output", "buffered", "VCC", "GND"]


def test_parse_subckt_instance_with_params():
    netlist = """
    .SUBCKT amp in out vdd W=1u
    M1 out in vdd vdd PMOS W=W
    .ENDS

    X1 sig out VCC amp W=2u gain=10
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    inst = result.instances[0]
    assert inst.subckt_name == "amp"
    assert ("W", "2u") in inst.parameters.keyed
    assert ("gain", "10") in inst.parameters.keyed


def test_subckt_wrong_net_count():
    netlist = """
    .SUBCKT buf in out
    R1 in out 1k
    .ENDS

    X1 a b c buf
    """.splitlines()

    parser = SpiceParser()
    with pytest.raises(SpiceFormatError) as exc_info:
        parser.parse(netlist)
    assert "expects 2 nets, got 3" in exc_info.value.reason


def test_subckt_undefined():
    netlist = """
    X1 a b c undefined_subckt
    """.splitlines()

    parser = SpiceParser()
    with pytest.raises(SpiceFormatError) as exc_info:
        parser.parse(netlist)
    assert "Unknown subcircuit" in exc_info.value.reason


def test_unclosed_subckt():
    netlist = """
    .SUBCKT test a b
    R1 a b 1k
    """.splitlines()

    parser = SpiceParser()
    with pytest.raises(SpiceFormatError) as exc_info:
        parser.parse(netlist)
    assert "Unclosed .SUBCKT" in exc_info.value.reason


def test_ends_without_subckt():
    netlist = """
    R1 a b 1k
    .ENDS
    """.splitlines()

    parser = SpiceParser()
    with pytest.raises(SpiceFormatError) as exc_info:
        parser.parse(netlist)
    assert ".ENDS without matching .SUBCKT" in exc_info.value.reason


def test_subckt_case_insensitive():
    netlist = """
    .subckt myinv in out
    R1 in out 1k
    .ends

    X1 a b myinv
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    assert "myinv" in result.subckts
    assert len(result.instances) == 1
    assert result.instances[0].subckt_name == "myinv"


def test_parse_vcvs():
    """Test voltage-controlled voltage source (E element)."""
    parser = SpiceParser()
    components = parser.parse(["E1 out+ out- ctrl+ ctrl- 10"]).instances

    assert len(components) == 1
    assert components[0].name == "E1"
    assert components[0].primitive == Primitive.VCVS
    assert components[0].nets == ["out+", "out-", "ctrl+", "ctrl-"]
    assert components[0].parameters.unkeyed == ["10"]


def test_parse_vccs():
    """Test voltage-controlled current source (G element)."""
    parser = SpiceParser()
    components = parser.parse(["G1 out+ out- ctrl+ ctrl- 1m"]).instances

    assert len(components) == 1
    assert components[0].name == "G1"
    assert components[0].primitive == Primitive.VCCS
    assert components[0].nets == ["out+", "out-", "ctrl+", "ctrl-"]
    assert components[0].parameters.unkeyed == ["1m"]


def test_parse_cccs():
    """Test current-controlled current source (F element)."""
    parser = SpiceParser()
    components = parser.parse(["F1 out+ out- Vsense 2"]).instances

    assert len(components) == 1
    assert components[0].name == "F1"
    assert components[0].primitive == Primitive.CCCS
    assert components[0].nets == ["out+", "out-"]
    assert components[0].parameters.unkeyed == ["Vsense", "2"]


def test_parse_ccvs():
    """Test current-controlled voltage source (H element)."""
    parser = SpiceParser()
    components = parser.parse(["H1 out+ out- Vsense 1k"]).instances

    assert len(components) == 1
    assert components[0].name == "H1"
    assert components[0].primitive == Primitive.CCVS
    assert components[0].nets == ["out+", "out-"]
    assert components[0].parameters.unkeyed == ["Vsense", "1k"]


def test_line_continuation():
    """Test that lines starting with + are joined to previous line."""
    netlist = """
    R1 node1 node2
    + 10k
    + param=value
    """.splitlines()

    parser = SpiceParser()
    components = parser.parse(netlist).instances

    assert len(components) == 1
    assert components[0].name == "R1"
    assert components[0].nets == ["node1", "node2"]
    assert components[0].parameters.unkeyed == ["10k"]
    assert ("param", "value") in components[0].parameters.keyed


def test_line_continuation_multiple():
    """Test multiple continuation lines and multiple components."""
    netlist = """
    E1 out 0
    + ctrl+ ctrl-
    + 100
    R1 out 0 1k
    """.splitlines()

    parser = SpiceParser()
    components = parser.parse(netlist).instances

    assert len(components) == 2
    assert components[0].primitive == Primitive.VCVS
    assert components[0].nets == ["out", "0", "ctrl+", "ctrl-"]
    assert components[0].parameters.unkeyed == ["100"]
    assert components[1].primitive == Primitive.RES


def test_controlled_sources_circuit():
    """Test a circuit using all controlled source types."""
    netlist = """
    V1 in 0 AC 1
    E1 amp1 0 in 0 10
    G1 amp2 0 in 0 1m
    Vsense amp1 mid 0
    F1 out1 0 Vsense 5
    H1 out2 0 Vsense 1k
    R1 out1 0 1k
    R2 out2 0 1k
    """.splitlines()

    parser = SpiceParser()
    components = parser.parse(netlist).instances

    assert len(components) == 8
    primitives = [c.primitive for c in components]
    assert Primitive.VCVS in primitives
    assert Primitive.VCCS in primitives
    assert Primitive.CCCS in primitives
    assert Primitive.CCVS in primitives


def test_wilson_current_mirror():
    """Test Wilson current mirror circuit (main.py example)."""
    netlist = """
    * Wilson current mirror

    Vcc vcc 0 DC 10

    * Reference current
    Rref vcc ref 10k

    * Q1: reference transistor
    Q1 ref base q1e NPN

    * Q3: feedback transistor
    Q3 q1e ref 0 NPN

    * Q2: output transistor
    Q2 out base 0 NPN

    * Output load
    Rload vcc out 1k
    """.splitlines()

    parser = SpiceParser()
    result = parser.parse(netlist)

    assert len(result.instances) == 6
    names = [c.name for c in result.instances]
    assert "Vcc" in names
    assert "Rref" in names
    assert "Q1" in names
    assert "Q2" in names
    assert "Q3" in names
    assert "Rload" in names

    # Verify BJTs
    bjts = [c for c in result.instances if c.primitive == Primitive.BJT]
    assert len(bjts) == 3
