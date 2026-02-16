import logging
import sys
from PySide6 import QtWidgets

from netlist_viewer.gui.netlist_view import NetlistView
from netlist_viewer.layout import PlacedNetlist


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netlist Viewer")
        self.setGeometry(0, 0, 800, 600)

        # Create and set the view as central widget
        self.view = NetlistView()
        self.setCentralWidget(self.view)

    def load_netlist(self, placed: PlacedNetlist):
        """Load a PlacedNetlist into the view."""
        self.view.load_netlist(placed)


def open_ui(netlist: PlacedNetlist):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.load_netlist(netlist)
    window.show()
    sys.exit(app.exec())


def cli_main():
    """CLI entry point for running netlist_viewer on a SPICE file."""
    import argparse
    from pathlib import Path
    from netlist_viewer.spice_parser import SpiceParser
    from netlist_viewer.layout import add_spring_locations

    parser = argparse.ArgumentParser(
        prog="netlist_viewer",
        description="Visualize SPICE netlists as interactive circuit diagrams",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to a SPICE netlist file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not args.file.exists():
        logging.error("File not found: %s", args.file)
        sys.exit(1)

    netlist_text = args.file.read_text()
    spice_parser = SpiceParser()
    netlist = spice_parser.parse(netlist_text)
    placed = add_spring_locations(netlist)
    open_ui(placed)
