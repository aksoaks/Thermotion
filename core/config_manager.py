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

CONFIG_FILE = "thermotion_config.json"

def load_config(self):
        """Load config from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                    self.update_display()
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not load config:\n{str(e)}")


def save_config(self):
    """Save config to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    except Exception as e:
        QMessageBox.warning(self, "Warning", f"Could not save config:\n{str(e)}")