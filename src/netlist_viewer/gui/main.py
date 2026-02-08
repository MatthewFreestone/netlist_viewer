import sys
import random
from PySide6 import QtCore, QtWidgets, QtGui

from src.netlist_viewer.gui.instance_graphics import ResistorItem


class NetlistView(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()

        # Create the scene (the canvas)
        self.scene = QtWidgets.QGraphicsScene()
        self.setScene(self.scene)
        
        # Configure view behavior
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)  # Pan with mouse
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        res = ResistorItem()
        self.scene.addItem(res)
        
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
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
    
def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())