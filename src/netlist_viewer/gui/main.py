import logging
import sys
from pathlib import Path
from PySide6 import QtWidgets, QtGui

from netlist_viewer.gui.netlist_view import NetlistView
from netlist_viewer.layout import add_spring_locations
from netlist_viewer.routing import RoutedNetlist, route_netlist
from netlist_viewer.spice_parser import SpiceParser


class HelpDialog(QtWidgets.QDialog):
    """Dialog showing keyboard shortcuts and help information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumWidth(300)

        layout = QtWidgets.QVBoxLayout(self)

        help_text = """
<h3>Keyboard Shortcuts</h3>
<table>
<tr>
    <td>R</td>
    <td>Rotate selected component 90°</td>
</tr>
</table>

<h3>Mouse Controls</h3>
<table>
<tr>
    <td>Left click</td>
    <td>Select item</td>
</tr>
<tr>
    <td>Right drag</td>
    <td>Pan view</td>
</tr>
<tr>
    <td>Scroll wheel</td>
    <td>Zoom in/out</td>
</tr>
</table>
"""
        label = QtWidgets.QLabel(help_text)
        label.setTextFormat(QtGui.Qt.TextFormat.RichText)
        layout.addWidget(label)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netlist Viewer")
        self.setGeometry(0, 0, 800, 600)

        # Create and set the view as central widget
        self.view = NetlistView()
        self.setCentralWidget(self.view)

        # Create menu bar
        self._create_menus()

    def _create_menus(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        open_action = QtGui.QAction("&Open...", self)
        open_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        shortcuts_action = QtGui.QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_help)
        help_menu.addAction(shortcuts_action)

    def _open_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open SPICE Netlist",
            "",
            "SPICE Files (*.spice *.cir *.sp *.net);;All Files (*)",
        )
        if not file_path:
            return

        try:
            text = Path(file_path).read_text()
            parser = SpiceParser()
            netlist = parser.parse(text)
            placed = add_spring_locations(netlist)
            routed = route_netlist(placed)
            self.load_netlist(routed)
            self.setWindowTitle(f"Netlist Viewer - {Path(file_path).name}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    def _show_help(self):
        dialog = HelpDialog(self)
        dialog.exec()

    def load_netlist(self, routed: RoutedNetlist):
        """Load a RoutedNetlist into the view."""
        self.view.load_netlist(routed)


def open_ui(routed: RoutedNetlist):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.load_netlist(routed)
    window.show()
    sys.exit(app.exec())


def cli_main():
    """CLI entry point for running netlist_viewer on a SPICE file."""
    import argparse

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

    assert isinstance(args.file, Path)

    if not args.file.exists():
        logging.error("File not found: %s", args.file)
        sys.exit(1)
    netlist_text = args.file.read_text()
    spice_parser = SpiceParser()
    netlist = spice_parser.parse(netlist_text)
    placed = add_spring_locations(netlist)
    routed = route_netlist(placed)
    open_ui(routed)
