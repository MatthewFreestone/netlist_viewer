from __future__ import annotations
from dataclasses import dataclass
import enum


class SpiceFormatError(BaseException):
    line: str
    reason: str
    def __init__(self, line, reason, *args):
        self.line = line
        self.reason = reason
        super().__init__(*args)
        self.add_note(f"{reason} @ {line}")

class SpiceParser():
    def parse(self, netlist: list[str]) -> Netlist:
        builder = NetlistBuilder()  
        for line in netlist:
            builder.handle_line(line)
        result = Netlist()
        result.instances = builder.scope
        result.global_nets = builder.global_nets
        return result
    
class Netlist:
    instances: list[Instance]
    subckts: dict[str, list[Instance]]
    global_nets: list[str]

class NetlistBuilder():
    build_stack: list
    scope: list[Instance]
    global_nets: list[str]
    def __init__(self):
        self.scope = []
        self.build_stack = []
        self.global_nets = ['0']
        pass

    def handle_line(self, line: str):
        if (SyntaxHelpers.is_comment(line)):
            return
        inst = Instance.from_line(line)
        self.scope.append(inst)

class SyntaxHelpers:
    def is_comment(line: str) -> bool:
        stripped = line.strip()
        if len(stripped) == 0:
            return True
        if stripped[0] == '#':
            return True
        return False

@dataclass
class Instance:
    primitive: Primitive
    nets: list[str]
    parameters: Parameters
    name: str

    def from_line(line: str) -> Instance:
        tokenized = line.strip().split() #TODO: Handle parenthesized expresions with spaces
        if len(tokenized) < 2:
            raise SpiceFormatError(line, "Unable to split into >= 2 tokens")
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
        k, sep, v = param.partition('=')
        if sep == '=':
            if k in self.keys:
                raise SpiceFormatError(param, "Unable to handle duplicate keys")
            self.keys.add(k)
            self.keyed.append((k, v))
        else:
            self.unkeyed.append(k)

class Primitive(enum.Enum):
    RES = 'R'
    CAP = 'C'
    VSOURCE = 'V'
    ISOURCE = 'I'
    UNKNOWN = '?'

    def terminal_count(self) -> int:
        match self:
            case Primitive.RES:
                return 2
            case Primitive.CAP:
                return 2
            case Primitive.ISOURCE:
                return 2
            case Primitive.VSOURCE:
                return 2
        return -1

    def from_name(name: str) -> Primitive:
        if len(name) == 0:
            raise SpiceFormatError(name, "No name provided")
        match name[0].upper():
            case Primitive.RES.value:
                return Primitive.RES
            case Primitive.CAP.value:
                return Primitive.CAP
            case Primitive.ISOURCE.value:
                return Primitive.ISOURCE
            case Primitive.VSOURCE.value:
                return Primitive.VSOURCE
        return Primitive.UNKNOWN