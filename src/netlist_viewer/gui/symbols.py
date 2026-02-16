"""Declarative symbol definitions for circuit components."""

from dataclasses import dataclass, field
from enum import Enum
from netlist_viewer.core_types import Number


class PinSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class Pin:
    """A connection point on a symbol."""

    name: str
    x: Number
    y: Number
    side: PinSide = PinSide.LEFT


@dataclass
class SymbolDef:
    """Declarative symbol definition - geometry and pins."""

    name: str
    width: Number
    height: Number
    pins: list[Pin]
    shapes: list[dict] = field(default_factory=list)


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
        {
            "type": "polyline",
            "points": [
                (-25, 0),
                (-20, -8),
                (-12, 8),
                (-4, -8),
                (4, 8),
                (12, -8),
                (20, 8),
                (25, 0),
            ],
        },
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "line", "p1": (-25, 0), "p2": (-5, 0)},
        {"type": "line", "p1": (-5, -10), "p2": (-5, 10)},
        {"type": "line", "p1": (5, -10), "p2": (5, 10)},
        {"type": "line", "p1": (5, 0), "p2": (25, 0)},
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "circle", "center": (0, 0), "r": 15},
        {"type": "line", "p1": (-25, 0), "p2": (-15, 0)},  # left lead
        {"type": "line", "p1": (15, 0), "p2": (25, 0)},  # right lead
        # Plus sign
        {"type": "line", "p1": (-10, 0), "p2": (-4, 0)},
        {"type": "line", "p1": (-7, -3), "p2": (-7, 3)},
        # Minus sign
        {"type": "line", "p1": (4, 0), "p2": (10, 0)},
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "circle", "center": (0, 0), "r": 15},
        {"type": "line", "p1": (-25, 0), "p2": (-15, 0)},  # left lead
        {"type": "line", "p1": (15, 0), "p2": (25, 0)},  # right lead
        # Arrow inside
        {"type": "line", "p1": (-8, 0), "p2": (8, 0)},
        {"type": "polygon", "points": [(8, 0), (3, -4), (3, 4)], "filled": True},
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "line", "p1": (0, 0), "p2": (0, 5)},
        {"type": "line", "p1": (-10, 5), "p2": (10, 5)},
        {"type": "line", "p1": (-6, 9), "p2": (6, 9)},
        {"type": "line", "p1": (-2, 13), "p2": (2, 13)},
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
        # Coil humps (4 arcs approximated as bumps)
        {"type": "line", "p1": (-25, 0), "p2": (-20, 0)},
        {"type": "arc", "center": (-15, 0), "r": 5, "start": 180, "span": 180},
        {"type": "arc", "center": (-5, 0), "r": 5, "start": 180, "span": 180},
        {"type": "arc", "center": (5, 0), "r": 5, "start": 180, "span": 180},
        {"type": "arc", "center": (15, 0), "r": 5, "start": 180, "span": 180},
        {"type": "line", "p1": (20, 0), "p2": (25, 0)},
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "line", "p1": (-25, 0), "p2": (-8, 0)},  # left lead
        # Triangle (anode side)
        {"type": "polygon", "points": [(-8, -10), (-8, 10), (8, 0)], "filled": False},
        # Bar (cathode side)
        {"type": "line", "p1": (8, -10), "p2": (8, 10)},
        {"type": "line", "p1": (8, 0), "p2": (25, 0)},  # right lead
        {"type": "terminal", "pos": (-25, 0)},
        {"type": "terminal", "pos": (25, 0)},
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
        {"type": "line", "p1": (0, -25), "p2": (0, -10)},
        # Emitter lead
        {"type": "line", "p1": (0, 25), "p2": (0, 10)},
        # Base lead
        {"type": "line", "p1": (-20, 0), "p2": (-5, 0)},
        # Vertical bar (base region)
        {"type": "line", "p1": (-5, -12), "p2": (-5, 12)},
        # Collector connection
        {"type": "line", "p1": (-5, -6), "p2": (0, -10)},
        # Emitter connection with arrow
        {"type": "line", "p1": (-5, 6), "p2": (0, 10)},
        # Arrow on emitter (pointing outward for NPN)
        {"type": "polygon", "points": [(0, 10), (-4, 5), (-1, 4)], "filled": True},
        {"type": "terminal", "pos": (0, -25)},
        {"type": "terminal", "pos": (-20, 0)},
        {"type": "terminal", "pos": (0, 25)},
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
        {"type": "line", "p1": (0, -30), "p2": (0, -10)},
        # Source lead
        {"type": "line", "p1": (0, 30), "p2": (0, 10)},
        # Gate lead
        {"type": "line", "p1": (-20, 0), "p2": (-10, 0)},
        # Gate vertical line
        {"type": "line", "p1": (-10, -12), "p2": (-10, 12)},
        # Channel (3 horizontal segments)
        {"type": "line", "p1": (-6, -10), "p2": (-6, -4)},
        {"type": "line", "p1": (-6, -2), "p2": (-6, 2)},
        {"type": "line", "p1": (-6, 4), "p2": (-6, 10)},
        # Drain connection
        {"type": "line", "p1": (-6, -10), "p2": (0, -10)},
        # Source connection
        {"type": "line", "p1": (-6, 10), "p2": (0, 10)},
        # Bulk connection
        {"type": "line", "p1": (-6, 0), "p2": (10, 0)},
        # Arrow on bulk (pointing in for NMOS)
        {"type": "polygon", "points": [(-2, 0), (2, -3), (2, 3)], "filled": True},
        {"type": "terminal", "pos": (0, -30)},
        {"type": "terminal", "pos": (-20, 0)},
        {"type": "terminal", "pos": (0, 30)},
        {"type": "terminal", "pos": (10, 0)},
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
        {"type": "line", "p1": (0, -25), "p2": (0, -10)},
        # Source lead
        {"type": "line", "p1": (0, 25), "p2": (0, 10)},
        # Channel (vertical bar)
        {"type": "line", "p1": (0, -10), "p2": (0, 10)},
        # Gate lead
        {"type": "line", "p1": (-20, 0), "p2": (-5, 0)},
        # Gate connection to channel
        {"type": "line", "p1": (-5, 0), "p2": (0, 0)},
        # Arrow on gate (pointing in for N-channel)
        {"type": "polygon", "points": [(0, 0), (-5, -3), (-5, 3)], "filled": True},
        {"type": "terminal", "pos": (0, -25)},
        {"type": "terminal", "pos": (-20, 0)},
        {"type": "terminal", "pos": (0, 25)},
    ],
)
