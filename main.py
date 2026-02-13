from src.netlist_viewer.layout import add_spring_locations
from src.netlist_viewer.gui.main import MainWindow
from src.netlist_viewer.spice_parser import SpiceParser
from PySide6 import QtWidgets
import sys

if __name__ == "__main__":
    netlist = """
    R1 1 2 1k
    R2 2 3 1k
    R3 3 0 1k
    C1 2 0 10u
    C2 2 0 10u
    C3 2 0 10u
    V1 1 0 DC 5""".splitlines()

    parser = SpiceParser()
    components = parser.parse(netlist)
    placed = add_spring_locations(components)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.load_netlist(placed)
    window.show()
    sys.exit(app.exec())