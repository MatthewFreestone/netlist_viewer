"""Declarative symbol definitions for circuit components."""

from dataclasses import dataclass, field
from enum import Enum


class PinSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class Pin:
    """A connection point on a symbol."""
    name: str
    x: float
    y: float
    side: PinSide = PinSide.LEFT


@dataclass
class SymbolDef:
    """Declarative symbol definition - geometry and pins."""
    name: str
    width: float
    height: float
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
        {"type": "polyline", "points": [
            (-25, 0), (-20, -8), (-12, 8), (-4, -8),
            (4, 8), (12, -8), (20, 8), (25, 0)
        ]},
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
        {"type": "line", "p1": (15, 0), "p2": (25, 0)},    # right lead
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
        {"type": "line", "p1": (15, 0), "p2": (25, 0)},    # right lead
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
