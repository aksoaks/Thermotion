import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QDialog, QLineEdit, QColorDialog, QListWidget,
                              QListWidgetItem, QCheckBox, QScrollArea, QGroupBox, QMessageBox,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QFont, QIcon, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError
from functools import partial

class ChannelConfigDialog(QDialog):
    def __init__(self, channel_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Settings")
        self.setFixedSize(400, 300)
        self.setStyleSheet("font-size: 12px;")

        self.channel_data = channel_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Channel Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Channel Name:"))
        self.name_edit = QLineEdit(self.channel_data["display_name"])
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Color Selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(50, 30)
        self.color_btn.setStyleSheet(f"background-color: {self.channel_data['color']};")
        self.color_btn.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_btn)

        layout.addLayout(color_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_btn.styleSheet().split(':')[1].split(';')[0]))
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def get_config(self):
        return {
            "display_name": self.name_edit.text(),
            "color": self.color_btn.styleSheet().split(':')[1].split(';')[0],
            "visible": True
        }
    
class DeviceScannerDialog(QDialog):
    config_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Configuration")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                font-size: 12px;
            }
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.devices = self.detect_devices()
        self.init_ui()

    def detect_devices(self):
        """Detect NI-DAQmx devices with module filtering"""
        try:
            system = nidaqmx.system.System.local()
            return [d for d in system.devices if "Mod" in d.name]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Device detection failed:\n{str(e)}")
            return []

    def init_ui(self):
        layout = QVBoxLayout()

        if not self.devices:
            layout.addWidget(QLabel("No NI-DAQmx modules detected"))
            retry_btn = QPushButton("Retry")
            retry_btn.clicked.connect(self.retry_detection)
            layout.addWidget(retry_btn)
            self.setLayout(layout)
            return

        # Device list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)

        self.device_widgets = []

        for device in self.devices:
            # Get module number and chassis name
            mod_num = device.name.split("Mod")[1]
            chassis = device.name.split("Mod")[0] + "Chassis"

            group = QGroupBox(f"{chassis} > Module {mod_num}")
            group.setCheckable(True)
            group.setChecked(True)

            layout_inner = QVBoxLayout()

            # Module display name
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Module Name:"))
            name_edit = QLineEdit(device.name)
            name_edit.setStyleSheet("font-size: 12px;")
            name_layout.addWidget(name_edit)
            layout_inner.addLayout(name_layout)

            # Channels
            channels_group = QGroupBox("Channels")
            channels_group.setStyleSheet("font-size: 12px;")
            channels_layout = QVBoxLayout()

            try:
                channels = [c.name.split('/')[-1] for c in device.ai_physical_chans]
                for ch in sorted(channels):
                    ch_layout = QHBoxLayout()

                    ch_layout.addWidget(QLabel(ch))
                    ch_layout.addStretch()

                    edit_btn = QPushButton("Edit")
                    edit_btn.setFixedWidth(80)
                    edit_btn.setStyleSheet("font-size: 12px;")
                    edit_btn.clicked.connect(partial(self.edit_channel, device.name, ch))

                    ch_layout.addWidget(edit_btn)
                    channels_layout.addLayout(ch_layout)

                channels_group.setLayout(channels_layout)
                layout_inner.addWidget(channels_group)

            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not read channels:\n{str(e)}")

            group.setLayout(layout_inner)
            scroll_layout.addWidget(group)
            self.device_widgets.append((group, name_edit, device))

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("font-size: 12px;")
        apply_btn.clicked.connect(self.apply_config)
        btn_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("font-size: 12px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def edit_channel(self, device_name, channel_name):
        """Edit individual channel settings"""
        channel_id = f"{device_name}/{channel_name}"
        channel_data = {
            "display_name": channel_name,
            "color": "#{:06x}".format(hash(channel_id) % 0xffffff),
            "visible": True
        }

        dialog = ChannelConfigDialog(channel_data, self)
        if dialog.exec() == QDialog.Accepted:
            print(f"Updated config for {channel_id}: {dialog.get_config()}")

    def apply_config(self):
        """Compile and emit final configuration"""
        config = {
            "version": 1,
            "devices": {}
        }

        for group, name_edit, device in self.device_widgets:
            if group.isChecked():
                config["devices"][device.name] = {
                    "display_name": name_edit.text(),
                    "channels": {}
                }

        self.config_updated.emit(config)
        self.accept()

    def retry_detection(self):
        """Retry device detection"""
        self.devices = self.detect_devices()
        self.init_ui()
