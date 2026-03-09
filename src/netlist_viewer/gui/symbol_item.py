from __future__ import annotations

from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QGraphicsPathItem,
    QStyleOptionGraphicsItem,
    QWidget,
    QStyle,
)
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPolygonF,
    QPainterPath,
    QPainterPathStroker,
)

from netlist_viewer.gui.symbols import (
    SymbolDef,
    Pin,
    PinSide,
    Shape,
    LineShape,
    PolylineShape,
    CircleShape,
    PolygonShape,
    ArcShape,
    TerminalShape,
    TextShape,
)
from netlist_viewer.core_types import Number
from netlist_viewer.layout import Point
from netlist_viewer.routing import BBox, _route_edge


class ConnectableItem(QGraphicsItem):
    """Base class for items that can be connected by wires."""

    connected_wires: list[WireItem]

    def pin_scene_pos(self, pin_name: str) -> QPointF:
        """Get scene position of a pin for wire connections."""
        raise NotImplementedError

    def get_pin_side(self, pin_name: str) -> PinSide | None:
        """Get the side a pin exits from. Override in subclasses with pin info."""
        return None


class WireItem(QGraphicsPathItem):
    """A wire connecting two graphics items, drawn as a polyline."""

    DEFAULT_COLOR = QColor(80, 80, 80)
    SELECTED_COLOR = QColor(255, 0, 0)

    def __init__(
        self,
        start_item: ConnectableItem,
        end_item: ConnectableItem,
        start_pin: str | None = None,
        end_pin: str | None = None,
        net: str | None = None,
        points: list[QPointF] | None = None,
    ):
        super().__init__()
        assert isinstance(start_pin, str) or isinstance(end_pin, str)
        self.start_item = start_item
        self.end_item = end_item
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.net = net
        self.sibling_wires: list[WireItem] = []  # Other wires on same net
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPen(QPen(self.DEFAULT_COLOR, 1.5))
        if points is not None:
            self.set_points(points)
        else:
            self.update_position()

    def set_points(self, points: list[QPointF]) -> None:
        """Set wire path from pre-computed waypoints."""
        if not points:
            return
        path = QPainterPath()
        path.moveTo(points[0])
        for pt in points[1:]:
            path.lineTo(pt)
        self.setPath(path)

    def shape(self) -> QPainterPath:
        """Return a narrow stroke around the wire for precise hit testing."""
        stroker = QPainterPathStroker()
        stroker.setWidth(8)  # Clickable width in pixels
        return stroker.createStroke(self.path())

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        # Highlight if this wire or any sibling on the same net is selected
        net_selected = self.isSelected() or any(
            w.isSelected() for w in self.sibling_wires
        )
        color = self.SELECTED_COLOR if net_selected else self.DEFAULT_COLOR
        self.setPen(QPen(color, 1.5))
        # Clear selection state to suppress Qt's default dotted rectangle
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            # Trigger repaint on all sibling wires so they update their color
            for wire in self.sibling_wires:
                wire.update()
            # Trigger repaint on connected items (for NetNodeItem to update)
            self.start_item.update()
            self.end_item.update()
            for wire in self.sibling_wires:
                wire.start_item.update()
                wire.end_item.update()
        return super().itemChange(change, value)

    def _get_pos(self, item: ConnectableItem, pin: str | None) -> QPointF:
        """Get position for connection - use pin if available, else center."""
        if pin is not None:
            return item.pin_scene_pos(pin)
        return item.scenePos()

    def _collect_bboxes(self) -> list[BBox]:
        """Collect bounding boxes of all SymbolItems in the scene."""
        scene = self.scene()
        if scene is None:
            return []

        bboxes: list[BBox] = []
        for item in scene.items():
            if isinstance(item, SymbolItem):
                rect = item.sceneBoundingRect()
                bboxes.append(
                    BBox(
                        left=rect.left(),
                        top=rect.top(),
                        right=rect.right(),
                        bottom=rect.bottom(),
                    )
                )
        return bboxes

    def update_position(self) -> None:
        """Update wire path with routing that avoids component bodies."""
        start_pos = self._get_pos(self.start_item, self.start_pin)
        end_pos = self._get_pos(self.end_item, self.end_pin)

        # Collect all component bboxes for routing
        all_bboxes = self._collect_bboxes()

        # Route using the routing module
        start_pt = Point(start_pos.x(), start_pos.y())
        end_pt = Point(end_pos.x(), end_pos.y())
        waypoints = _route_edge(start_pt, end_pt, all_bboxes)

        # Convert waypoints to path
        path = QPainterPath()
        path.moveTo(QPointF(waypoints[0].x, waypoints[0].y))
        for pt in waypoints[1:]:
            path.lineTo(QPointF(pt.x, pt.y))

        self.setPath(path)


class NetNodeItem(ConnectableItem):
    """A small dot representing a net junction point."""

    def __init__(self, x: float = 0, y: float = 0, name: str = ""):
        super().__init__()
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)
        self.setZValue(1)  # Above wires (default z=0)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def boundingRect(self) -> QRectF:
        return QRectF(-5, -5, 10, 10)

    def _is_net_selected(self) -> bool:
        """Check if any wire connected to this node is selected."""
        for wire in self.connected_wires:
            if wire.isSelected() or any(w.isSelected() for w in wire.sibling_wires):
                return True
        return False

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        /,
        widget: QWidget | None = None,
    ) -> None:
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QColor(0, 0, 0))
        elif self._is_net_selected():
            painter.setPen(QPen(QColor(255, 0, 0), 1))
            painter.setBrush(QColor(255, 0, 0))
        else:
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QColor(150, 150, 150))
        painter.drawEllipse(QPointF(0, 0), 4, 4)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def pin_scene_pos(self, pin_name: str) -> QPointF:
        """Net nodes have a single implicit pin at center."""
        return self.scenePos()


class SymbolItem(ConnectableItem):
    """Generic renderer for any SymbolDef."""

    def __init__(
        self,
        symbol: SymbolDef,
        name: str = "",
        params: str = "",
        x: float = 0,
        y: float = 0,
        orient: int = 0,
    ):
        super().__init__()
        self.symbol = symbol
        self.name = name
        self.params = params
        self.orientation = orient  # 0, 90, 180, 270 degrees
        self.connected_wires: list[WireItem] = []

        self.setPos(x, y)
        self._setup_flags()
        self._create_labels()

    def _setup_flags(self):
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def _create_labels(self):
        self.name_label = QGraphicsTextItem(self.name, self)
        self.name_label.setPos(-15, -30)

        self.value_label = QGraphicsTextItem(self.params, self)
        self.value_label.setPos(-15, 15)

    def _rotate_point(self, x: Number, y: Number) -> tuple[Number, Number]:
        """Rotate a point by self.orient degrees around origin."""
        match self.orientation:
            case 0:
                return (x, y)
            case 90:
                return (-y, x)
            case 180:
                return (-x, -y)
            case 270:
                return (y, -x)
            case _:
                return (x, y)

    def get_pin(self, pin_name: str) -> Pin | None:
        """Get a pin by name."""
        for pin in self.symbol.pins:
            if pin.name == pin_name:
                return pin
        return None

    def get_pin_side(self, pin_name: str) -> PinSide | None:
        """Get the rotated side of a pin (accounting for component orientation)."""
        pin = self.get_pin(pin_name)
        if pin is None:
            return None

        # Rotate the pin side based on component orientation
        side = pin.side
        rotations = self.orientation // 90
        sides_cw = [PinSide.TOP, PinSide.RIGHT, PinSide.BOTTOM, PinSide.LEFT]
        try:
            idx = sides_cw.index(side)
            rotated_idx = (idx + rotations) % 4
            return sides_cw[rotated_idx]
        except ValueError:
            return side

    def pin_local_pos(self, pin_name: str) -> QPointF:
        """Get local position of a pin (relative to item origin)."""
        pin = self.get_pin(pin_name)
        if pin is None:
            return QPointF(0, 0)
        rx, ry = self._rotate_point(pin.x, pin.y)
        return QPointF(rx, ry)

    def pin_scene_pos(self, pin_name: str) -> QPointF:
        """Get scene position of a pin (for wire connections)."""
        return self.scenePos() + self.pin_local_pos(pin_name)

    def boundingRect(self) -> QRectF:
        w, h = self.symbol.width, self.symbol.height
        if self.orientation in (90, 270):
            w, h = h, w
        margin = 5
        return QRectF(-w / 2 - margin, -h / 2 - margin, w + 2 * margin, h + 2 * margin)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        /,
        widget: QWidget | None = None,
    ) -> None:
        color = QColor(255, 0, 0) if self.isSelected() else QColor(0, 0, 0)
        pen = QPen(color, 2)
        painter.setPen(pen)

        for shape in self.symbol.shapes:
            self._draw_shape(painter, shape, color)

    def _draw_shape(self, painter: QPainter, shape: Shape, color: QColor) -> None:
        match shape:
            case LineShape(p1, p2):
                rp1 = self._rotate_point(*p1)
                rp2 = self._rotate_point(*p2)
                painter.drawLine(QPointF(*rp1), QPointF(*rp2))

            case PolylineShape(points):
                qpoints = [QPointF(*self._rotate_point(*p)) for p in points]
                painter.drawPolyline(QPolygonF(qpoints))

            case CircleShape(center, r):
                cx, cy = self._rotate_point(*center)
                painter.drawEllipse(QPointF(cx, cy), r, r)

            case PolygonShape(points, filled):
                qpoints = [QPointF(*self._rotate_point(*p)) for p in points]
                if filled:
                    painter.setBrush(color)
                painter.drawPolygon(QPolygonF(qpoints))
                painter.setBrush(QColor(0, 0, 0, 0))  # reset

            case ArcShape(center, r, start, span):
                cx, cy = self._rotate_point(*center)
                rotated_start = start + self.orientation
                # Qt uses 1/16th degree units
                rect = QRectF(cx - r, cy - r, r * 2, r * 2)
                painter.drawArc(rect, int(rotated_start * 16), int(span * 16))

            case TerminalShape(pos):
                px, py = self._rotate_point(*pos)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(px, py), 2, 2)

            case TextShape(pos, text, anchor):
                px, py = self._rotate_point(*pos)
                font = painter.font()
                font.setPointSize(8)
                painter.setFont(font)
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()
                if anchor == "right":
                    px -= text_width
                elif anchor == "center":
                    px -= text_width / 2
                painter.drawText(QPointF(px, py + text_height / 4), text)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def set_orient(self, orient: int) -> None:
        """Set orientation and update display."""
        self.orientation = orient % 360
        self.prepareGeometryChange()
        self.update()
        for wire in self.connected_wires:
            wire.update_position()

    def rotate_by(self, degrees: int) -> None:
        """Rotate by given degrees (snapped to 90)."""
        self.set_orient(self.orientation + degrees)
