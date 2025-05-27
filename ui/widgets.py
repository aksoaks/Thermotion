import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QDialog, QLineEdit, QColorDialog, QListWidget,
                              QListWidgetItem, QCheckBox, QScrollArea, QGroupBox, QMessageBox,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QFont
from PySide6.QtGui import QColor, QIcon, QFont, QIcon, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError
from functools import partial

class ChannelListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                font-size: 12px;
            }
            QListWidget::item {
                height: 28px;
            }
        """)
        self.module_widgets = {}  # Initialisation ajoutée ici
        self.graph_items = {}

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.data(Qt.UserRole):
            self.parent().edit_channel(item.data(Qt.UserRole))
        super().mouseDoubleClickEvent(event)
