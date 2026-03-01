# netlist_viewer

Visualize SPICE netlists as interactive circuit diagrams.

netlist_viewer parses SPICE netlist files and renders them as schematic diagrams using automatic graph layout. Built with NetworkX for layout algorithms and PySide6 (Qt) for the GUI.

## Installation

```bash
pip install netlist_viewer
```

Requires Python 3.13+.

## Usage

### Command Line

```bash
netlist_viewer path/to/circuit.spice
```

or, using `uv`:

```bash
uvx netlist_viewer path/to/circuit.spice
```

Options:
- `-v, --verbose` — Enable verbose logging

### From Python

```python
from netlist_viewer.spice_parser import SpiceParser
from netlist_viewer.layout import add_spring_locations
from netlist_viewer.gui.main import open_ui

netlist_text = """
V1 in 0 AC 1
R1 in mid 100
L1 mid out 10m
C1 out 0 1u
"""

parser = SpiceParser()
netlist = parser.parse(netlist_text)
placed = add_spring_locations(netlist)
open_ui(placed)
```

## Controls

| Input | Action |
|-------|--------|
| Left click | Select component |
| Right drag | Pan view |
| Scroll wheel | Zoom in/out |
| R | Rotate selected component 90 degrees |
| Ctrl+O | Open file |

## Supported SPICE Primitives

| Prefix | Component | Terminals |
|--------|-----------|-----------|
| R | Resistor | 2 |
| C | Capacitor | 2 |
| L | Inductor | 2 |
| D | Diode | 2 |
| Q | BJT | 3 (C, B, E) |
| M | MOSFET | 4 (D, G, S, B) |
| J | JFET | 3 (D, G, S) |
| V | Voltage Source | 2 |
| I | Current Source | 2 |
| X | Subcircuit | Variable |

Subcircuits (`.SUBCKT` / `.ENDS`) are supported and rendered as labeled boxes.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run type checker
uv run ty check

# Run linter
uv run ruff check

# Run the viewer with a sample netlist
uv run main.py
```

## License

MIT
