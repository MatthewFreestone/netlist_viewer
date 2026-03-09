from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
import enum
import logging
import time


class SpiceFormatError(BaseException):
    line: str
    reason: str

    def __init__(self, line, reason, *args):
        self.line = line
        self.reason = reason
        super().__init__(*args)
        self.add_note(f"{reason} @ {line}")


@dataclass(frozen=True)
class SubcktDef:
    name: str
    ports: list[str]
    instances: list[Instance]
    parameters: Parameters


class SpiceParser:
    def parse(self, syntax: str | Sequence[str]) -> Netlist:
        start_time = time.time()
        builder = NetlistBuilder()
        if isinstance(syntax, str):
            syntax = syntax.splitlines()

        # Handle line continuations (lines starting with +)
        syntax = self._join_continuations(list(syntax))

        for line in syntax:
            builder.handle_line(line)

        if builder.build_stack:
            raise SpiceFormatError("", "Unclosed .SUBCKT definition")

        result = Netlist(builder.scope, builder.subckts, builder.global_nets)
        end_time = time.time()
        logging.info("Parsed netlist in %f s", end_time - start_time)
        return result

    def _join_continuations(self, lines: list[str]) -> list[str]:
        """Join continuation lines (starting with +) to the previous line."""
        result: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("+") and result:
                # Append to previous line (strip the + and leading whitespace)
                result[-1] = result[-1] + " " + stripped[1:].lstrip()
            else:
                result.append(line)
        return result


@dataclass(frozen=True)
class Netlist:
    instances: list[Instance]
    subckts: dict[str, SubcktDef]
    global_nets: list[str]


@dataclass(frozen=True)
class _InProgressSubckt:
    name: str
    ports: list[str]
    parameters: Parameters
    parent_scope: list[Instance]


class NetlistBuilder:
    build_stack: list[_InProgressSubckt]
    scope: list[Instance]
    subckts: dict[str, SubcktDef]
    global_nets: list[str]

    def __init__(self):
        self.scope = []
        self.build_stack = []
        self.subckts = {}
        self.global_nets = ["0"]

    def handle_line(self, line: str):
        if SyntaxHelpers.is_comment_or_whitespace(line):
            return

        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith(".SUBCKT"):
            self._handle_subckt_start(stripped)
            return

        if upper.startswith(".ENDS"):
            self._handle_subckt_end(stripped)
            return

        # Handle X (subcircuit instance) lines
        if upper.startswith("X"):
            inst = self._parse_subckt_instance(stripped)
        else:
            inst = Instance.from_line(line)

        self.scope.append(inst)

    def _handle_subckt_start(self, line: str):
        # .SUBCKT name port1 port2 ... [param=value ...]
        tokens = line.split()
        if len(tokens) < 2:
            raise SpiceFormatError(line, ".SUBCKT requires a name")

        name = tokens[1]
        ports: list[str] = []
        parameters = Parameters()

        for token in tokens[2:]:
            if "=" in token:
                parameters.add(token)
            else:
                ports.append(token)

        # Push current scope onto stack and start new scope
        new_frame = _InProgressSubckt(name, ports, parameters, self.scope)
        self.build_stack.append(new_frame)
        self.scope = []

    def _handle_subckt_end(self, line: str):
        if len(self.build_stack) == 0:
            raise SpiceFormatError(line, ".ENDS without matching .SUBCKT")

        finished_frame = self.build_stack.pop()

        # Create subckt definition
        subckt = SubcktDef(
            name=finished_frame.name,
            ports=finished_frame.ports,
            instances=self.scope,
            parameters=finished_frame.parameters,
        )
        self.subckts[finished_frame.name] = subckt

        # Restore parent scope
        self.scope = finished_frame.parent_scope

    def _parse_subckt_instance(self, line: str) -> Instance:
        # Xname net1 net2 ... subckt_name [param=value ...]
        # our normal way doesn't work to due variable terminal count
        tokens = line.split()
        if len(tokens) < 2:
            raise SpiceFormatError(line, "X instance requires nets and subckt name")

        inst_name = tokens[0]

        # Find the subckt name by scanning tokens for a known subckt
        subckt_name = None
        subckt_idx = -1

        for i, token in enumerate(tokens[1:], start=1):
            if "=" in token:
                # This is a parameter, subckt name must be before this
                break
            if token in self.subckts:
                subckt_name = token
                subckt_idx = i
                break

        if subckt_name is None:
            # Grab the last token to use in the name as the error
            non_param_tokens = [t for t in tokens[1:] if "=" not in t]
            if non_param_tokens:
                attempted_name = non_param_tokens[-1]
                raise SpiceFormatError(line, f"Unknown subcircuit '{attempted_name}'")
            raise SpiceFormatError(line, "No subcircuit name found")

        subckt_def = self.subckts[subckt_name]
        expected_nets = len(subckt_def.ports)
        nets = tokens[1:subckt_idx]

        if len(nets) != expected_nets:
            raise SpiceFormatError(
                line,
                f"Subcircuit '{subckt_name}' expects {expected_nets} nets, got {len(nets)}",
            )

        # Parse parameters after subckt name
        parameters = Parameters()
        for token in tokens[subckt_idx + 1 :]:
            parameters.add(token)

        return Instance(
            primitive=Primitive.SUBCKT,
            nets=nets,
            parameters=parameters,
            name=inst_name,
            subckt_name=subckt_name,
        )


class SyntaxHelpers:
    def is_comment_or_whitespace(line: str) -> bool:
        stripped = line.strip()
        if len(stripped) == 0:
            return True
        if stripped[0] == "#" or stripped[0] == "*":
            return True
        return False


@dataclass(frozen=True)
class Instance:
    primitive: Primitive
    nets: list[str]
    parameters: Parameters
    name: str
    subckt_name: str | None = None

    def from_line(line: str) -> Instance:
        # TODO: Handle parenthesized expresions with spaces
        tokenized = line.strip().split()

        if len(tokenized) < 2:
            raise SpiceFormatError(
                line, "Unable to split into instance into name and nets"
            )

        name_token, *rest = tokenized
        prim: Primitive = Primitive.from_name(name_token)
        if prim == Primitive.UNKNOWN:
            raise SpiceFormatError(line, f"Unknown primitive for inst '{name_token}'")
        n_terminal = prim.terminal_count()
        if len(rest) < n_terminal:
            raise SpiceFormatError(line, "Not enough nets provided")

        nets = rest[:n_terminal]
        parameters = Parameters()
        for param in rest[n_terminal:]:
            parameters.add(param)
        return Instance(prim, nets, parameters, name_token)


class Parameters:
    keys: set[str]
    unkeyed: list[str]
    keyed: list[tuple[str, str]]

    def __init__(self):
        self.keys = set()
        self.keyed = []
        self.unkeyed = []

    def add(self, param: str):
        k, sep, v = param.partition("=")
        if sep == "=":
            if k in self.keys:
                raise SpiceFormatError(param, "Unable to handle duplicate keys")
            self.keys.add(k)
            self.keyed.append((k, v))
        else:
            self.unkeyed.append(k)


class Primitive(enum.Enum):
    RES = "R"
    CAP = "C"
    IND = "L"
    DIODE = "D"
    BJT = "Q"
    MOSFET = "M"
    JFET = "J"
    VSOURCE = "V"
    ISOURCE = "I"
    VCVS = "E"  # Voltage-controlled voltage source
    VCCS = "G"  # Voltage-controlled current source
    CCCS = "F"  # Current-controlled current source
    CCVS = "H"  # Current-controlled voltage source
    SUBCKT = "X"
    UNKNOWN = "?"

    def terminal_count(self) -> int:
        match self:
            case Primitive.RES | Primitive.CAP | Primitive.IND | Primitive.DIODE:
                return 2
            case Primitive.ISOURCE | Primitive.VSOURCE:
                return 2
            case Primitive.CCCS | Primitive.CCVS:
                return 2  # F/H: out+, out- (Vname reference is a parameter)
            case Primitive.BJT | Primitive.JFET:
                return 3
            case Primitive.MOSFET | Primitive.VCVS | Primitive.VCCS:
                return 4  # E/G: out+, out-, ctrl+, ctrl-
            case Primitive.SUBCKT:
                return -1  # Variable, determined by subckt definition
        return -1

    def from_name(name: str) -> Primitive:
        if len(name) == 0:
            raise SpiceFormatError(name, "No name provided")
        prefix = name[0].upper()
        for prim in Primitive:
            if prim.value == prefix and prim != Primitive.UNKNOWN:
                return prim
        return Primitive.UNKNOWN
