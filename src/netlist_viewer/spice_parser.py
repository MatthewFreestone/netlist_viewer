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
    def parse(self, netlist: list[str]) -> list[Instance]:
        builder = NetlistBuilder()  
        for line in netlist:
            builder.handle_line(line)
        return builder.scope

class NetlistBuilder():
    build_stack: list
    scope: list[Instance]
    def __init__(self):
        self.scope = []
        self.build_stack = []
        pass

    def handle_line(self, line: str):
        inst = Instance.from_line(line)
        self.scope.append(inst)

@dataclass
class Instance:
    primitive: Primitive
    nets: list[str]
    parameters: dict[str, str]
    name: str

    def from_line(line: str) -> Instance:
        tokenized = line.strip().split()
        if len(tokenized) < 2:
            raise SpiceFormatError(line, "Unable to split into >= 2 tokens")
        prim = Primitive.from_name(tokenized[0])
        port1 = tokenized[1]
        port2 = tokenized[2]
        parameters = dict()
        for param in tokenized[3:]:
            k, sep, v = param.partition('=')
            if sep != '':
                parameters[k] = v
        return Instance(prim, [port1, port2], parameters, tokenized[0])

class Primitive(enum.Enum):
    RES = 'R'
    CAP = 'C'
    VSOURCE = 'V'
    ISOURCE = 'I'
    UNKNOWN = '?'

    def from_name(name: str) -> Primitive:
        if len(name) == 0:
            return Primitive.UNKNOWN
        match name[0]:
            case Primitive.RES:
                return Primitive.RES
            case Primitive.CAP:
                return Primitive.CAP
            case Primitive.ISOURCE:
                return Primitive.ISOURCE
            case Primitive.VSOURCE:
                return Primitive.VSOURCE
        return Primitive.UNKNOWN