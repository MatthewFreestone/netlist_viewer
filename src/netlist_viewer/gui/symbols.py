"""Declarative symbol definitions for circuit components."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal
from netlist_viewer.core_types import Number


class PinSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


# Type alias for coordinate pairs
Point = tuple[Number, Number]


# Shape dataclasses
@dataclass(frozen=True)
class LineShape:
    p1: Point
    p2: Point


@dataclass(frozen=True)
class PolylineShape:
    points: tuple[Point, ...]


@dataclass(frozen=True)
class CircleShape:
    center: Point
    r: Number


@dataclass(frozen=True)
class PolygonShape:
    points: tuple[Point, ...]
    filled: bool = False


@dataclass(frozen=True)
class ArcShape:
    center: Point
    r: Number
    start: Number
    span: Number


@dataclass(frozen=True)
class TerminalShape:
    pos: Point


@dataclass(frozen=True)
class TextShape:
    pos: Point
    text: str
    anchor: Literal["left", "right", "center"] = "left"


Shape = (
    LineShape
    | PolylineShape
    | CircleShape
    | PolygonShape
    | ArcShape
    | TerminalShape
    | TextShape
)


@dataclass(frozen=True)
class Pin:
    """A connection point on a symbol."""

    name: str
    x: Number
    y: Number
    side: PinSide = PinSide.LEFT


@dataclass(frozen=True)
class SymbolDef:
    """Declarative symbol definition - geometry and pins."""

    name: str
    width: Number
    height: Number
    pins: list[Pin]
    shapes: list[Shape]


def create_subckt_symbol(subckt_name: str, port_names: list[str]) -> SymbolDef:
    """Dynamically create a SymbolDef for a subcircuit instance.

    Creates a rectangular box with ports distributed on left and right sides.
    """
    n_ports = len(port_names)
    if n_ports == 0:
        # Edge case: no ports
        return SymbolDef(
            name=subckt_name,
            width=60,
            height=40,
            pins=[],
            shapes=[
                PolygonShape(
                    points=((-30, -20), (30, -20), (30, 20), (-30, 20)),
                    filled=False,
                ),
            ],
        )

    # Split ports between left and right sides
    left_count = (n_ports + 1) // 2
    right_count = n_ports - left_count

    # Calculate dimensions based on port count
    port_spacing = 25
    min_height = 40
    height = max(min_height, max(left_count, right_count) * port_spacing + 20)
    width = 80
    half_w = width // 2
    half_h = height // 2

    pins: list[Pin] = []
    shapes: list[Shape] = []

    # Box outline
    shapes.append(
        PolygonShape(
            points=(
                (-half_w, -half_h),
                (half_w, -half_h),
                (half_w, half_h),
                (-half_w, half_h),
            ),
            filled=False,
        )
    )

    # Left side ports
    for i in range(left_count):
        port_name = port_names[i]
        # Distribute evenly along left edge
        if left_count == 1:
            y = 0
        else:
            y = (
                -half_h + 15 + i * (height - 30) / (left_count - 1)
                if left_count > 1
                else 0
            )
        x = -half_w - 15

        pins.append(Pin(str(i + 1), x, y, PinSide.LEFT))
        shapes.append(LineShape(p1=(x, y), p2=(-half_w, y)))
        shapes.append(TerminalShape(pos=(x, y)))
        shapes.append(TextShape(pos=(-half_w + 3, y), text=port_name, anchor="left"))

    # Right side ports
    for i in range(right_count):
        port_idx = left_count + i
        port_name = port_names[port_idx]
        # Distribute evenly along right edge
        if right_count == 1:
            y = 0
        else:
            y = (
                -half_h + 15 + i * (height - 30) / (right_count - 1)
                if right_count > 1
                else 0
            )
        x = half_w + 15

        pins.append(Pin(str(port_idx + 1), x, y, PinSide.RIGHT))
        shapes.append(LineShape(p1=(half_w, y), p2=(x, y)))
        shapes.append(TerminalShape(pos=(x, y)))
        shapes.append(TextShape(pos=(half_w - 3, y), text=port_name, anchor="right"))

    return SymbolDef(
        name=subckt_name,
        width=width + 30,  # Account for lead lines
        height=height,
        pins=pins,
        shapes=shapes,
    )


# Symbol library
RESISTOR = SymbolDef(
    name="resistor",
    width=50,
    height=20,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),
        Pin("2", 25, 0, PinSide.RIGHT),
    ],
    shapes=[
        PolylineShape(
            points=(
                (-25, 0),
                (-20, -8),
                (-12, 8),
                (-4, -8),
                (4, 8),
                (12, -8),
                (20, 8),
                (25, 0),
            )
        ),
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

CAPACITOR = SymbolDef(
    name="capacitor",
    width=50,
    height=20,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),
        Pin("2", 25, 0, PinSide.RIGHT),
    ],
    shapes=[
        LineShape(p1=(-25, 0), p2=(-5, 0)),
        LineShape(p1=(-5, -10), p2=(-5, 10)),
        LineShape(p1=(5, -10), p2=(5, 10)),
        LineShape(p1=(5, 0), p2=(25, 0)),
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

VOLTAGE_SOURCE = SymbolDef(
    name="voltage_source",
    width=50,
    height=30,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),  # positive
        Pin("2", 25, 0, PinSide.RIGHT),  # negative
    ],
    shapes=[
        CircleShape(center=(0, 0), r=15),
        LineShape(p1=(-25, 0), p2=(-15, 0)),  # left lead
        LineShape(p1=(15, 0), p2=(25, 0)),  # right lead
        # Plus sign
        LineShape(p1=(-10, 0), p2=(-4, 0)),
        LineShape(p1=(-7, -3), p2=(-7, 3)),
        # Minus sign
        LineShape(p1=(4, 0), p2=(10, 0)),
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

CURRENT_SOURCE = SymbolDef(
    name="current_source",
    width=50,
    height=30,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),
        Pin("2", 25, 0, PinSide.RIGHT),
    ],
    shapes=[
        CircleShape(center=(0, 0), r=15),
        LineShape(p1=(-25, 0), p2=(-15, 0)),  # left lead
        LineShape(p1=(15, 0), p2=(25, 0)),  # right lead
        # Arrow inside
        LineShape(p1=(-8, 0), p2=(8, 0)),
        PolygonShape(points=((8, 0), (3, -4), (3, 4)), filled=True),
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

GROUND = SymbolDef(
    name="ground",
    width=20,
    height=15,
    pins=[
        Pin("1", 0, 0, PinSide.TOP),
    ],
    shapes=[
        LineShape(p1=(0, 0), p2=(0, 5)),
        LineShape(p1=(-10, 5), p2=(10, 5)),
        LineShape(p1=(-6, 9), p2=(6, 9)),
        LineShape(p1=(-2, 13), p2=(2, 13)),
    ],
)

INDUCTOR = SymbolDef(
    name="inductor",
    width=50,
    height=20,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),
        Pin("2", 25, 0, PinSide.RIGHT),
    ],
    shapes=[
        # Coil humps (4 arcs)
        LineShape(p1=(-25, 0), p2=(-20, 0)),
        ArcShape(center=(-15, 0), r=5, start=180, span=180),
        ArcShape(center=(-5, 0), r=5, start=180, span=180),
        ArcShape(center=(5, 0), r=5, start=180, span=180),
        ArcShape(center=(15, 0), r=5, start=180, span=180),
        LineShape(p1=(20, 0), p2=(25, 0)),
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

DIODE = SymbolDef(
    name="diode",
    width=50,
    height=20,
    pins=[
        Pin("1", -25, 0, PinSide.LEFT),  # Anode
        Pin("2", 25, 0, PinSide.RIGHT),  # Cathode
    ],
    shapes=[
        LineShape(p1=(-25, 0), p2=(-8, 0)),  # left lead
        # Triangle (anode side)
        PolygonShape(points=((-8, -10), (-8, 10), (8, 0)), filled=False),
        # Bar (cathode side)
        LineShape(p1=(8, -10), p2=(8, 10)),
        LineShape(p1=(8, 0), p2=(25, 0)),  # right lead
        TerminalShape(pos=(-25, 0)),
        TerminalShape(pos=(25, 0)),
    ],
)

# BJT NPN Transistor - pins: 1=Collector, 2=Base, 3=Emitter
BJT = SymbolDef(
    name="bjt",
    width=40,
    height=50,
    pins=[
        Pin("1", 0, -25, PinSide.TOP),  # Collector
        Pin("2", -20, 0, PinSide.LEFT),  # Base
        Pin("3", 0, 25, PinSide.BOTTOM),  # Emitter
    ],
    shapes=[
        # Collector lead
        LineShape(p1=(0, -25), p2=(0, -10)),
        # Emitter lead
        LineShape(p1=(0, 25), p2=(0, 10)),
        # Base lead
        LineShape(p1=(-20, 0), p2=(-5, 0)),
        # Vertical bar (base region)
        LineShape(p1=(-5, -12), p2=(-5, 12)),
        # Collector connection
        LineShape(p1=(-5, -6), p2=(0, -10)),
        # Emitter connection with arrow
        LineShape(p1=(-5, 6), p2=(0, 10)),
        # Arrow on emitter (pointing outward for NPN)
        PolygonShape(points=((0, 10), (-4, 5), (-1, 4)), filled=True),
        TerminalShape(pos=(0, -25)),
        TerminalShape(pos=(-20, 0)),
        TerminalShape(pos=(0, 25)),
    ],
)

# MOSFET NMOS - pins: 1=Drain, 2=Gate, 3=Source, 4=Bulk
MOSFET = SymbolDef(
    name="mosfet",
    width=40,
    height=60,
    pins=[
        Pin("1", 0, -30, PinSide.TOP),  # Drain
        Pin("2", -20, 0, PinSide.LEFT),  # Gate
        Pin("3", 0, 30, PinSide.BOTTOM),  # Source
        Pin("4", 10, 0, PinSide.RIGHT),  # Bulk
    ],
    shapes=[
        # Drain lead
        LineShape(p1=(0, -30), p2=(0, -10)),
        # Source lead
        LineShape(p1=(0, 30), p2=(0, 10)),
        # Gate lead
        LineShape(p1=(-20, 0), p2=(-10, 0)),
        # Gate vertical line
        LineShape(p1=(-10, -12), p2=(-10, 12)),
        # Channel (3 horizontal segments)
        LineShape(p1=(-6, -10), p2=(-6, -4)),
        LineShape(p1=(-6, -2), p2=(-6, 2)),
        LineShape(p1=(-6, 4), p2=(-6, 10)),
        # Drain connection
        LineShape(p1=(-6, -10), p2=(0, -10)),
        # Source connection
        LineShape(p1=(-6, 10), p2=(0, 10)),
        # Bulk connection
        LineShape(p1=(-6, 0), p2=(10, 0)),
        # Arrow on bulk (pointing in for NMOS)
        PolygonShape(points=((-2, 0), (2, -3), (2, 3)), filled=True),
        TerminalShape(pos=(0, -30)),
        TerminalShape(pos=(-20, 0)),
        TerminalShape(pos=(0, 30)),
        TerminalShape(pos=(10, 0)),
    ],
)

# JFET N-channel - pins: 1=Drain, 2=Gate, 3=Source
JFET = SymbolDef(
    name="jfet",
    width=40,
    height=50,
    pins=[
        Pin("1", 0, -25, PinSide.TOP),  # Drain
        Pin("2", -20, 0, PinSide.LEFT),  # Gate
        Pin("3", 0, 25, PinSide.BOTTOM),  # Source
    ],
    shapes=[
        # Drain lead
        LineShape(p1=(0, -25), p2=(0, -10)),
        # Source lead
        LineShape(p1=(0, 25), p2=(0, 10)),
        # Channel (vertical bar)
        LineShape(p1=(0, -10), p2=(0, 10)),
        # Gate lead
        LineShape(p1=(-20, 0), p2=(-5, 0)),
        # Gate connection to channel
        LineShape(p1=(-5, 0), p2=(0, 0)),
        # Arrow on gate (pointing in for N-channel)
        PolygonShape(points=((0, 0), (-5, -3), (-5, 3)), filled=True),
        TerminalShape(pos=(0, -25)),
        TerminalShape(pos=(-20, 0)),
        TerminalShape(pos=(0, 25)),
    ],
)
