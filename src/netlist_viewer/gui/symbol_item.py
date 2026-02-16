"""Generic symbol renderer for circuit components."""

from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QGraphicsLineItem,
    QStyleOptionGraphicsItem,
    QWidget,
)
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF

from netlist_viewer.gui.symbols import SymbolDef, Pin


class WireItem(QGraphicsLineItem):
    """A wire connecting two graphics items, optionally at specific pins."""

    def __init__(
        self,
        start_item: QGraphicsItem,
        end_item: QGraphicsItem,
        start_pin: str | None = None,
        end_pin: str | None = None,
    ):
        super().__init__()
        assert isinstance(start_pin, str) or isinstance(end_pin, str)
        self.start_item = start_item
        self.end_item = end_item
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.setPen(QPen(QColor(80, 80, 80), 1.5))
        self.update_position()

    def _get_pos(self, item: QGraphicsItem, pin: str | None) -> QPointF:
        """Get position for connection - use pin if available, else center."""
        if pin is not None:
            pin_method = getattr(item, "pin_scene_pos", None)
            if pin_method is not None:
                return pin_method(pin)
        return item.scenePos()

    def update_position(self):
        """Update wire endpoints based on connected items' positions."""
        start_pos = self._get_pos(self.start_item, self.start_pin)
        end_pos = self._get_pos(self.end_item, self.end_pin)
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())


class NetNodeItem(QGraphicsItem):
    """A small dot representing a net junction point."""

    def __init__(self, x: float = 0, y: float = 0, name: str = ""):
        super().__init__()
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def boundingRect(self) -> QRectF:
        return QRectF(-5, -5, 10, 10)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        /,
        widget: QWidget | None = None,
    ) -> None:
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


class SymbolItem(QGraphicsItem):
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
        self.orient = orient  # 0, 90, 180, 270 degrees
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

    def _rotate_point(self, x: float, y: float) -> tuple[float, float]:
        """Rotate a point by self.orient degrees around origin."""
        match self.orient:
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
        if self.orient in (90, 270):
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

    def _draw_shape(self, painter: QPainter, shape: dict, color: QColor) -> None:
        match shape["type"]:
            case "line":
                p1 = self._rotate_point(*shape["p1"])
                p2 = self._rotate_point(*shape["p2"])
                painter.drawLine(QPointF(*p1), QPointF(*p2))

            case "polyline":
                points = [QPointF(*self._rotate_point(*p)) for p in shape["points"]]
                painter.drawPolyline(QPolygonF(points))

            case "circle":
                cx, cy = self._rotate_point(*shape["center"])
                painter.drawEllipse(QPointF(cx, cy), shape["r"], shape["r"])

            case "polygon":
                points = [QPointF(*self._rotate_point(*p)) for p in shape["points"]]
                if shape.get("filled", False):
                    painter.setBrush(color)
                painter.drawPolygon(QPolygonF(points))
                painter.setBrush(QColor(0, 0, 0, 0))  # reset

            case "arc":
                cx, cy = self._rotate_point(*shape["center"])
                r = shape["r"]
                start = shape["start"] + self.orient
                span = shape["span"]
                # Qt uses 1/16th degree units
                rect = QRectF(cx - r, cy - r, r * 2, r * 2)
                painter.drawArc(rect, int(start * 16), int(span * 16))

            case "terminal":
                px, py = self._rotate_point(*shape["pos"])
                painter.setBrush(color)
                painter.drawEllipse(QPointF(px, py), 2, 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def set_orient(self, orient: int) -> None:
        """Set orientation and update display."""
        self.orient = orient % 360
        self.prepareGeometryChange()
        self.update()
        for wire in self.connected_wires:
            wire.update_position()

    def rotate_by(self, degrees: int) -> None:
        """Rotate by given degrees (snapped to 90)."""
        self.set_orient(self.orient + degrees)
