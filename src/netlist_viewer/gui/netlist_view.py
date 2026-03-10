import logging
import math
from PySide6 import QtCore, QtWidgets, QtGui

from netlist_viewer.gui.symbol_item import SymbolItem, WireItem, NetNodeItem
from netlist_viewer.gui.symbols import (
    RESISTOR,
    CAPACITOR,
    INDUCTOR,
    DIODE,
    BJT,
    MOSFET,
    JFET,
    VOLTAGE_SOURCE,
    CURRENT_SOURCE,
    VCVS,
    VCCS,
    CCCS,
    CCVS,
    create_subckt_symbol,
)
from netlist_viewer.layout import PlacedInstance, NET_INDICATOR
from netlist_viewer.routing import RoutedNetlist
from netlist_viewer.spice_parser import Primitive, Instance, Netlist


# Map primitive types to symbol definitions
PRIMITIVE_SYMBOLS = {
    Primitive.RES: RESISTOR,
    Primitive.CAP: CAPACITOR,
    Primitive.IND: INDUCTOR,
    Primitive.DIODE: DIODE,
    Primitive.BJT: BJT,
    Primitive.MOSFET: MOSFET,
    Primitive.JFET: JFET,
    Primitive.VSOURCE: VOLTAGE_SOURCE,
    Primitive.ISOURCE: CURRENT_SOURCE,
    Primitive.VCVS: VCVS,
    Primitive.VCCS: VCCS,
    Primitive.CCCS: CCCS,
    Primitive.CCVS: CCVS,
}


class NetlistView(QtWidgets.QGraphicsView):
    # Scale factor to convert nx layout coords (-1 to 1) to screen coords
    LAYOUT_SCALE = 300.0

    def __init__(self):
        super().__init__()

        # Create the scene (the canvas)
        self._scene = QtWidgets.QGraphicsScene()
        self.setScene(self._scene)

        # Configure view behavior
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

    def load_netlist(self, routed: RoutedNetlist) -> None:
        """Load a RoutedNetlist and populate the scene with graphics items."""
        self._scene.clear()

        # Maps to look up graphics items by their node key
        instance_items: list[SymbolItem] = []
        net_node_items: dict[str, NetNodeItem] = {}

        # Create graphics items for each placed instance
        for idx, placed_inst in enumerate(routed.instances):
            inst = placed_inst.instance
            x = placed_inst.location.x * self.LAYOUT_SCALE
            y = placed_inst.location.y * self.LAYOUT_SCALE
            params_str = " ".join(inst.parameters.unkeyed)

            item = self._create_item_for_primitive(
                inst, x, y, params_str, routed.source
            )
            self._scene.addItem(item)
            instance_items.append(item)

        # Create graphics items for net junction nodes
        for net_name, placed_net in routed.net_nodes.items():
            x = placed_net.location.x * self.LAYOUT_SCALE
            y = placed_net.location.y * self.LAYOUT_SCALE
            node_item = NetNodeItem(x, y, net_name)
            self._scene.addItem(node_item)
            net_node_items[net_name] = node_item

        # Auto-orient instances based on neighbor positions
        self._auto_orient_instances(routed, instance_items, net_node_items)

        # Draw wires from pre-computed routes
        # Track wires by net so we can link siblings
        wires_by_net: dict[str, list[WireItem]] = {}

        for routed_wire in routed.wires:
            start_key = routed_wire.start
            end_key = routed_wire.end
            net = routed_wire.net

            logging.debug(f"Creating wire for {routed_wire}")

            start_item: SymbolItem | NetNodeItem
            end_item: SymbolItem | NetNodeItem
            if isinstance(start_key, int):
                start_item = instance_items[start_key]
            else:
                start_item = net_node_items[start_key]

            if isinstance(end_key, int):
                end_item = instance_items[end_key]
            else:
                end_item = net_node_items[end_key]

            # Convert Point waypoints to QPointF
            points = [QtCore.QPointF(pt.x, pt.y) for pt in routed_wire.points]

            wire = WireItem(
                start_item,
                end_item,
                routed_wire.start_pin,
                routed_wire.end_pin,
                net=net,
                points=points,
            )
            self._scene.addItem(wire)

            # Register wire with both connected items
            start_item.connected_wires.append(wire)
            end_item.connected_wires.append(wire)

            # Track for sibling linking
            if net not in wires_by_net:
                wires_by_net[net] = []
            wires_by_net[net].append(wire)

        # Link sibling wires on the same net
        for net, wires in wires_by_net.items():
            for wire in wires:
                wire.sibling_wires = [w for w in wires if w is not wire]

        # Re-route all wires using actual pin positions from SymbolItems
        # (routing.py uses component centers, not actual pin offsets)
        # Use immediate routing for initial setup (no debounce)
        for wires in wires_by_net.values():
            for wire in wires:
                wire.update_position_immediate()

        # Fit the view to show all items
        self.fitInView(
            self._scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )

    def _auto_orient_instances(
        self,
        routed: RoutedNetlist,
        instance_items: list[SymbolItem],
        net_node_items: dict[str, NetNodeItem],
    ) -> None:
        """Compute and apply optimal orientation for each instance based on neighbors."""

        for idx, placed_inst in enumerate(routed.instances):
            item = instance_items[idx]
            inst = placed_inst.instance
            item_pos = item.pos()

            # Group neighbor positions by which pin they connect to
            pin_neighbors: dict[str, list[QtCore.QPointF]] = {}
            for pin_idx, net in enumerate(inst.nets):
                pin_name = str(pin_idx + 1)
                pin_neighbors[pin_name] = []

                # Find neighbors connected via this net
                for edge in routed.edges:
                    if edge.net != net:
                        continue
                    # Check if this instance is part of this edge
                    other_key: int | str | None = None
                    if edge.start == idx:
                        other_key = edge.end
                    elif edge.end == idx:
                        other_key = edge.start
                    else:
                        continue

                    # Get position of the other endpoint
                    if isinstance(other_key, int):
                        other_pos = instance_items[other_key].pos()
                    else:
                        net_node_key = NET_INDICATOR + str(net)
                        if net_node_key in net_node_items:
                            other_pos = net_node_items[net_node_key].pos()
                        else:
                            continue
                    pin_neighbors[pin_name].append(other_pos)

            # Compute best orientation for 2-pin devices
            if len(inst.nets) == 2:
                orient = self._compute_best_orient(
                    item_pos, pin_neighbors.get("1", []), pin_neighbors.get("2", [])
                )
                item.set_orient(orient)

    def _compute_best_orient(
        self,
        item_pos: QtCore.QPointF,
        pin1_neighbors: list[QtCore.QPointF],
        pin2_neighbors: list[QtCore.QPointF],
    ) -> int:
        """Compute best orientation (0, 90, 180, 270) based on neighbor positions."""
        if not pin1_neighbors and not pin2_neighbors:
            return 0

        # Average position of each pin's neighbors
        def avg_pos(positions: list[QtCore.QPointF]) -> QtCore.QPointF:
            if not positions:
                return item_pos
            x = sum(p.x() for p in positions) / len(positions)
            y = sum(p.y() for p in positions) / len(positions)
            return QtCore.QPointF(x, y)

        p1_avg = avg_pos(pin1_neighbors)
        p2_avg = avg_pos(pin2_neighbors)

        # Vector from pin1's neighbors to pin2's neighbors
        dx = p2_avg.x() - p1_avg.x()
        dy = p2_avg.y() - p1_avg.y()

        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return 0

        # Angle of this vector
        angle = math.atan2(dy, dx)
        # Convert to degrees and snap to nearest 90
        degrees = math.degrees(angle)
        snapped = round(degrees / 90) * 90
        return int(snapped) % 360

    def _find_pin_for_net(self, instance_nets: PlacedInstance, net: str) -> str | None:
        """Find which pin (by name) connects to the given net."""
        try:
            pin_index = instance_nets.instance.nets.index(net)
            # Pin names are "1", "2", etc. (1-indexed)
            return str(pin_index + 1)
        except ValueError:
            logging.warning(
                "Unable to find net %s for instance %s in list %s",
                net,
                instance_nets.get_name(),
                ",".join(instance_nets.instance.nets),
            )
            return None

    def _create_item_for_primitive(
        self, inst: Instance, x: float, y: float, params: str, netlist: Netlist
    ):
        """Create the appropriate graphics item for a given primitive type."""
        primitive = inst.primitive

        if primitive == Primitive.SUBCKT:
            # Look up subcircuit definition to get port names
            subckt_name = inst.subckt_name
            if subckt_name and subckt_name in netlist.subckts:
                subckt_def = netlist.subckts[subckt_name]
                symbol = create_subckt_symbol(subckt_name, subckt_def.ports)
            else:
                # Fallback: create generic box with numbered ports
                port_names = [str(i + 1) for i in range(len(inst.nets))]
                symbol = create_subckt_symbol(subckt_name or "?", port_names)
        elif primitive not in PRIMITIVE_SYMBOLS:
            logging.warning("Unable to locate %s, falling back to resistor", primitive)
            symbol = RESISTOR
        else:
            symbol = PRIMITIVE_SYMBOLS[primitive]

        return SymbolItem(symbol, name=inst.name, params=params, x=x, y=y)

    def mousePressEvent(self, event):
        """Enable panning when clicking on empty space."""
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Clicked on empty space - enable panning
                self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
                # Create a fake press event to start the drag
                fake_event = QtGui.QMouseEvent(
                    event.type(),
                    event.position(),
                    event.globalPosition(),
                    QtCore.Qt.MouseButton.LeftButton,
                    event.buttons(),
                    event.modifiers(),
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

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == QtCore.Qt.Key.Key_R:
            # Rotate selected items by 90 degrees
            for item in self._scene.selectedItems():
                if isinstance(item, SymbolItem):
                    item.rotate_by(90)
            event.accept()
        else:
            super().keyPressEvent(event)
