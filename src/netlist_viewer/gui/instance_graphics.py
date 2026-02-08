from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QPolygonF
class ResistorItem(QGraphicsItem):

    def __init__(self, x=0, y=0, name:str = "R", params:str =""):
        super().__init__()
        self.value = params
        self.name = name
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