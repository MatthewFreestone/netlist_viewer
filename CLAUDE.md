## Purpose
SPICE netlist to interactive Qt GUI viewer. Uses NetworkX for graph layout and PySide6 for rendering.

## Project Structure
```
main.py                           # Entry point - parse, layout, launch GUI
src/netlist_viewer/
├── spice_parser.py               # SPICE text parsing
├── layout.py                     # NetworkX graph construction & positioning
└── gui/
    ├── main.py                   # MainWindow, NetlistView (QGraphicsView)
    ├── symbols.py                # Declarative symbol definitions (SymbolDef, Pin)
    └── symbol_item.py            # Generic SymbolItem renderer
tests/
└── test_spice_parser.py          # Parser and layout tests
```

## Data Flow
```
SPICE text → SpiceParser → Netlist → to_nx_graph() → nx.Graph
           → add_spring_locations() → PlacedNetlist → NetlistView → Qt scene
```

## Key Classes

### spice_parser.py
- `SpiceParser`: Parses SPICE text into `Netlist`
- `Netlist`: Contains `instances: list[Instance]` and `global_nets`
- `Instance`: Dataclass with `primitive`, `nets`, `parameters`, `name`
- `Primitive`: Enum - `RES`, `CAP`, `VSOURCE`, `ISOURCE`
- `Parameters`: Keyed (`param=value`) and unkeyed params
- `SpiceFormatError`: Parsing exception with line context

### layout.py
- `to_nx_graph(netlist)`: Converts to NetworkX graph
  - Direct edges for 2-terminal nets
  - Virtual net nodes for nets with >2 connections
- `add_spring_locations(netlist)`: Returns `PlacedNetlist`
  - Uses `planar_layout` if planar, else `spring_layout`
- `PlacedNetlist`: Contains `PlacedInstance` list and `PlacedNet` dict
- `Point`: Named tuple `(x, y)`

### gui/symbols.py
- `SymbolDef`: Declarative symbol definition with `name`, `width`, `height`, `pins`, `shapes`
- `Pin`: Connection point with `name`, `x`, `y`, `side`
- `PinSide`: Enum - `LEFT`, `RIGHT`, `TOP`, `BOTTOM`
- Built-in symbols: `RESISTOR`, `CAPACITOR`, `VOLTAGE_SOURCE`, `CURRENT_SOURCE`, `GROUND`
- Shapes are dicts with `type` key: `line`, `polyline`, `circle`, `polygon`, `terminal`

### gui/symbol_item.py
- `SymbolItem`: Generic QGraphicsItem that renders any `SymbolDef`
  - Supports rotation via `orient` (0, 90, 180, 270)
  - `pin_scene_pos(pin_name)`: Get world position of a pin for wire routing
  - Movable/selectable, highlights red when selected
- `WireItem`: Connects items, optionally at specific pins
- `NetNodeItem`: Grey dot for net junctions

### gui/main.py
- `MainWindow`: Top-level QMainWindow
- `NetlistView`: QGraphicsView with pan (RMB drag) and zoom (wheel)
- `PRIMITIVE_SYMBOLS`: Maps `Primitive` enum to `SymbolDef`
- `LAYOUT_SCALE = 300.0`: Converts spring coords to screen space

## Adding New Symbols
1. Define a new `SymbolDef` in `symbols.py` with pins and shapes
2. Add mapping in `PRIMITIVE_SYMBOLS` dict in `gui/main.py`

## Supported SPICE Primitives
- `R` (Resistor): 2 terminals
- `C` (Capacitor): 2 terminals
- `V` (Voltage Source): 2 terminals
- `I` (Current Source): 2 terminals

## Dependencies
- `networkx`: Graph algorithms and layout
- `pyside6`: Qt bindings
- `scipy`: Used by NetworkX spring layout

## Running
```bash
uv run python main.py
```

## Testing
```bash
uv run pytest
```
