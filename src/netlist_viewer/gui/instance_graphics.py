from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QPolygonF


class WireItem(QGraphicsLineItem):
    """A wire connecting two graphics items, updating when they move."""

    def __init__(self, start_item: QGraphicsItem, end_item: QGraphicsItem):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(QColor(80, 80, 80), 1.5))
        self.update_position()

    def update_position(self):
        """Update wire endpoints based on connected items' positions."""
        start_pos = self.start_item.pos()
        end_pos = self.end_item.pos()
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())


class NetNodeItem(QGraphicsItem):
    """A small dot representing a net junction point."""

    def __init__(self, x=0, y=0, name: str = ""):
        super().__init__()
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def boundingRect(self):
        return QRectF(-5, -5, 10, 10)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(100, 100, 100), 1)
        painter.setPen(pen)
        painter.setBrush(QColor(150, 150, 150))
        painter.drawEllipse(QPointF(0, 0), 4, 4)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)
    

class ResistorItem(QGraphicsItem):
    """A squigle representing a resistor."""

    def __init__(self, x=0, y=0, name: str = "R", params: str = ""):
        super().__init__()
        self.value = params
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        # Make it movable and selectable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Create child text items for labels
        self.name_label = QGraphicsTextItem(self.name, self)
        self.name_label.setPos(-15, -25)

        self.value_label = QGraphicsTextItem(self.value, self)
        self.value_label.setPos(-15, 15)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def boundingRect(self):
        """Define the bounding box for this item"""
        return QRectF(-30, -20, 60, 40)
    
    def paint(self, painter, option, widget):
        """Draw the resistor symbol"""
        # Set pen for drawing
        pen = QPen(QColor(0, 0, 0), 2)
        if self.isSelected():
            pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)
        
        # Draw zigzag resistor symbol
        points = [
            QPointF(-25, 0),
            QPointF(-20, -8),
            QPointF(-12, 8),
            QPointF(-4, -8),
            QPointF(4, 8),
            QPointF(12, -8),
            QPointF(20, 8),
            QPointF(25, 0)
        ]
        painter.drawPolyline(QPolygonF(points))
        
        # Draw connection points (terminals)
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(QPointF(-25, 0), 2, 2)
        painter.drawEllipse(QPointF(25, 0), 2, 2)


class CapacitorItem(QGraphicsItem):
    """A capacitor symbol."""

    def __init__(self, x=0, y=0, name: str = "C", params: str = ""):
        super().__init__()
        self.value = params
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self.name_label = QGraphicsTextItem(self.name, self)
        self.name_label.setPos(-15, -25)

        self.value_label = QGraphicsTextItem(self.value, self)
        self.value_label.setPos(-15, 15)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def boundingRect(self):
        return QRectF(-30, -20, 60, 40)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(0, 0, 0), 2)
        if self.isSelected():
            pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)

        # draw two parallel lines and nodes
        painter.drawLine(QPointF(-25, 0), QPointF(-5, 0))
        painter.drawLine(QPointF(-5, -10), QPointF(-5, 10))
        painter.drawLine(QPointF(5, -10), QPointF(5, 10))
        painter.drawLine(QPointF(5, 0), QPointF(25, 0))

        # draw connection points
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(QPointF(-25, 0), 2, 2)
        painter.drawEllipse(QPointF(25, 0), 2, 2)


class VoltageSourceItem(QGraphicsItem):
    """A voltage source symbol"""

    def __init__(self, x=0, y=0, name: str = "V", params: str = ""):
        super().__init__()
        self.value = params
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self.name_label = QGraphicsTextItem(self.name, self)
        self.name_label.setPos(-15, -35)

        self.value_label = QGraphicsTextItem(self.value, self)
        self.value_label.setPos(-15, 20)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def boundingRect(self):
        return QRectF(-30, -25, 60, 50)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(0, 0, 0), 2)
        if self.isSelected():
            pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)

        # Draw circle for source
        painter.drawEllipse(QPointF(0, 0), 15, 15)
        # Draw leads
        painter.drawLine(QPointF(-25, 0), QPointF(-15, 0))
        painter.drawLine(QPointF(15, 0), QPointF(25, 0))
        # Draw + and - inside
        painter.drawLine(QPointF(-10, 0), QPointF(-4, 0))
        painter.drawLine(QPointF(-7, -3), QPointF(-7, 3))
        painter.drawLine(QPointF(4, 0), QPointF(10, 0))

        # Draw connection points
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(QPointF(-25, 0), 2, 2)
        painter.drawEllipse(QPointF(25, 0), 2, 2)


class CurrentSourceItem(QGraphicsItem):
    """A current source symbol (circle with arrow)."""

    def __init__(self, x=0, y=0, name: str = "I", params: str = ""):
        super().__init__()
        self.value = params
        self.name = name
        self.connected_wires: list[WireItem] = []
        self.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self.name_label = QGraphicsTextItem(self.name, self)
        self.name_label.setPos(-15, -35)

        self.value_label = QGraphicsTextItem(self.value, self)
        self.value_label.setPos(-15, 20)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for wire in self.connected_wires:
                wire.update_position()
        return super().itemChange(change, value)

    def boundingRect(self):
        return QRectF(-30, -25, 60, 50)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(0, 0, 0), 2)
        if self.isSelected():
            pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)

        # Draw circle for source
        painter.drawEllipse(QPointF(0, 0), 15, 15)
        # Draw leads
        painter.drawLine(QPointF(-25, 0), QPointF(-15, 0))
        painter.drawLine(QPointF(15, 0), QPointF(25, 0))
        # Draw arrow inside (pointing right)
        painter.drawLine(QPointF(-8, 0), QPointF(8, 0))
        # Arrowhead
        arrow_points = [
            QPointF(8, 0),
            QPointF(3, -4),
            QPointF(3, 4),
        ]
        painter.setBrush(pen.color())
        painter.drawPolygon(QPolygonF(arrow_points))

        # Draw connection points
        painter.drawEllipse(QPointF(-25, 0), 2, 2)
        painter.drawEllipse(QPointF(25, 0), 2, 2)