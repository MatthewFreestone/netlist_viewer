import sys
from PySide6 import QtCore, QtWidgets, QtGui

from src.netlist_viewer.gui.instance_graphics import (
    ResistorItem,
    CapacitorItem,
    VoltageSourceItem,
    CurrentSourceItem,
    WireItem,
    NetNodeItem,
)
from src.netlist_viewer.layout import PlacedNetlist
from src.netlist_viewer.spice_parser import Primitive


class NetlistView(QtWidgets.QGraphicsView):
    # Scale factor to convert spring layout coords (typically -1 to 1) to screen coords
    LAYOUT_SCALE = 300.0

    def __init__(self):
        super().__init__()

        # Create the scene (the canvas)
        self.scene = QtWidgets.QGraphicsScene()
        self.setScene(self.scene)

        # Configure view behavior
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def load_netlist(self, placed: PlacedNetlist):
        """Load a PlacedNetlist and populate the scene with graphics items."""
        self.scene.clear()

        # Maps to look up graphics items by their node key
        instance_items: dict[int, QtWidgets.QGraphicsItem] = {}
        net_node_items: dict[str, NetNodeItem] = {}

        # Create graphics items for each placed instance
        for idx, placed_inst in enumerate(placed.instances):
            inst = placed_inst.instance
            x = placed_inst.location.x * self.LAYOUT_SCALE
            y = placed_inst.location.y * self.LAYOUT_SCALE
            params_str = " ".join(inst.parameters.unkeyed)

            item = self._create_item_for_primitive(inst.primitive, x, y, inst.name, params_str)
            self.scene.addItem(item)
            instance_items[idx] = item

        # Create graphics items for net junction nodes
        for net_name, placed_net in placed.net_nodes.items():
            x = placed_net.location.x * self.LAYOUT_SCALE
            y = placed_net.location.y * self.LAYOUT_SCALE
            node_item = NetNodeItem(x, y, net_name)
            self.scene.addItem(node_item)
            net_node_items[net_name] = node_item

        # Draw wires for edges, connecting items
        for edge in placed.edges:
            start_key, end_key = edge
            start_item = instance_items[start_key] if isinstance(start_key, int) else net_node_items[start_key]
            end_item = instance_items[end_key] if isinstance(end_key, int) else net_node_items[end_key]

            wire = WireItem(start_item, end_item)
            self.scene.addItem(wire)

            # Register wire with both connected items
            start_item.connected_wires.append(wire)
            end_item.connected_wires.append(wire)

        # Fit the view to show all items
        self.fitInView(self.scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)

    def _create_item_for_primitive(self, primitive: Primitive, x: float, y: float, name: str, params: str):
        """Create the appropriate graphics item for a given primitive type."""
        match primitive:
            case Primitive.RES:
                return ResistorItem(x, y, name, params)
            case Primitive.CAP:
                return CapacitorItem(x, y, name, params)
            case Primitive.VSOURCE:
                return VoltageSourceItem(x, y, name, params)
            case Primitive.ISOURCE:
                return CurrentSourceItem(x, y, name, params)
            case _:
                # Fallback to a generic resistor-style item for unknown types
                return ResistorItem(x, y, name, params)

    def mousePressEvent(self, event):
        """Enable panning when clicking on empty space."""
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Clicked on empty space - enable panning
                self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
                # Create a fake press event to start the drag
                fake_event = QtGui.QMouseEvent(
                    event.type(), event.position(), event.globalPosition(),
                    QtCore.Qt.MouseButton.LeftButton, event.buttons(), event.modifiers()
                )
                super().mousePressEvent(fake_event)
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Reset drag mode after panning."""
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def wheelEvent(self, event):
        """Zoom with mouse wheel."""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)


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
    
def main(netlist: PlacedNetlist):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.load_netlist(netlist)
    window.show()
    sys.exit(app.exec())