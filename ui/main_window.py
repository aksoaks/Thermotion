import os
import sys
import json
from functools import partial

# Ajouter la racine du projet au PYTHONPATH si nécessaire
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QDialog, QLineEdit, QColorDialog, QListWidget,
                              QListWidgetItem, QCheckBox, QScrollArea, QGroupBox, QMessageBox,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QFont, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError

from ui.dialogs import ChannelConfigDialog, DeviceScannerDialog
from ui.widgets import ChannelListWidget
from utils.style import MAIN_WINDOW_STYLE, CONTROL

CONFIG_FILE = "config.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = "c:/user/SF66405/Code/Python/cDAQ/icon.jpg"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Icon file not found at {icon_path}")
        self.setWindowTitle("Thermotion - Debug Interface")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                font-size: 12px;
            }
            QPushButton {
                font-size: 12px;
                min-height: 25px;
            }
            QLabel {
                font-size: 12px;
            }
        """)

        self.config = {}
        self.module_widgets = {}  # Initialisation du dictionnaire
        self.graph_items = {}
        self.init_ui()
        self.load_config()
    
        if self.config.get("devices"):
            self.update_display()
            self.check_devices_online()  # Ajoutez cette ligne

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        # Graph Area
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Voltage', 'V')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        layout.addWidget(self.plot_widget, 75)  # 75% width

        # Control Panel
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)

        # Title
        title = QLabel("Active Channels")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        control_layout.addWidget(title)

        # Channel List
        self.channel_list = ChannelListWidget(self)
        control_layout.addWidget(self.channel_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.scan_btn = QPushButton("Scan Devices")
        self.scan_btn.clicked.connect(self.scan_devices)
        btn_layout.addWidget(self.scan_btn)

        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_measurement)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        btn_layout.addWidget(self.stop_btn)

        control_layout.addLayout(btn_layout)
        layout.addWidget(control_panel, 25)  # 25% width

    def load_config(self):
        """Load config from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                    self.update_display()
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not load config:\n{str(e)}")

    def check_devices_online(self):
        """Check if configured devices are online"""
        try:
            system = nidaqmx.system.System.local()
            online_devices = [d.name for d in system.devices]
            
            for module_name in self.module_widgets:
                device_name = next((k for k,v in self.config["devices"].items() 
                                if v["display_name"] == module_name), None)
                if device_name and device_name not in online_devices:
                    # Add offline indicator
                    for i in range(self.channel_list.count()):
                        item = self.channel_list.item(i)
                        widget = self.channel_list.itemWidget(item)
                        if widget and module_name in widget.text():
                            # Add offline label
                            offline_label = QLabel("(offline)")
                            offline_label.setStyleSheet("color: red;")
                            layout = widget.layout()
                            if layout:
                                layout.addWidget(offline_label)
        except Exception as e:
            print(f"Device check error: {str(e)}")

    def save_config(self):
        """Save config to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not save config:\n{str(e)}")

    def scan_devices(self):
        """Open device scanner dialog"""
        dialog = DeviceScannerDialog(self)
        dialog.config_updated.connect(self.update_config)
        dialog.exec()

    def update_config(self, new_config):
        """Update configuration"""
        self.config = new_config
        self.save_config()
        self.update_display()

    def update_display(self):
        """Update UI based on current config"""
        self.plot_widget.clear()
        self.channel_list.clear()
        self.graph_items = {}

        # Initialize module_widgets if not exists (safety check)
        if not hasattr(self, 'module_widgets'):
            self.module_widgets = {}
        else:
            self.module_widgets.clear()

        if not self.config.get("devices"):
            self.start_btn.setEnabled(False)
            return

        # Organize channels by module
        modules = {}
        for device_name, device_cfg in self.config["devices"].items():
            module_name = device_cfg.get("display_name", device_name)
            if module_name not in modules:
                modules[module_name] = {
                    "device_name": device_name,
                    "channels": []
                }

            # Add simulated channels (replace with real channels)
            for channel_id, channel_data in device_cfg.get("channels", {}).items():
                modules[module_name]["channels"].append({
                    "id": channel_id,
                    "display_name": channel_data["display_name"],
                    "color": channel_data["color"],
                    "visible": channel_data["visible"]
                })

        # Add modules to display
        for i, (module_name, module_data) in enumerate(modules.items()):
            # Add separator line between modules (except first one)
            if i > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color: #888; margin: 5px 0;")

                separator_item = QListWidgetItem()
                separator_item.setFlags(separator_item.flags() & ~Qt.ItemIsSelectable)
                separator_item.setSizeHint(QSize(0, 1))  # Thin separator line
                self.channel_list.addItem(separator_item)
                self.channel_list.setItemWidget(separator_item, separator)

            # Module header with visibility control
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(5, 5, 5, 5)

            # Module visibility checkbox
            module_cb = QCheckBox()
            module_cb.setChecked(True)
            module_cb.stateChanged.connect(
                lambda state, mn=module_name: self.toggle_module_visibility(mn, state)
            )
            header_layout.addWidget(module_cb)

            # Centered module name
            name_label = QLabel(module_name)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            """)
            header_layout.addWidget(name_label, 1)  # Stretchable

            header_item = QListWidgetItem()
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            header_item.setSizeHint(header_widget.sizeHint())
            self.channel_list.addItem(header_item)
            self.channel_list.setItemWidget(header_item, header_widget)

            # Store module reference
            self.module_widgets[module_name] = {
                'checkbox': module_cb,
                'channels': [ch['id'] for ch in module_data["channels"]]
            }

            # Add channels
            for channel in module_data["channels"]:
                # Create plot item
                curve = self.plot_widget.plot(
                    [0, 1, 2, 3, 4],  # X values (time)
                    [0, 1, 4, 9, 16], # Y values (simulated data)
                    name=channel["display_name"],
                    pen=pg.mkPen(color=channel["color"], width=2)
                )

                # Create channel list item
                item = QListWidgetItem()
                item.setData(Qt.UserRole, channel["id"])

                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(2, 2, 2, 2)

                # Visibility checkbox
                cb = QCheckBox()
                cb.setChecked(True)
                cb.stateChanged.connect(
                    lambda state, cid=channel["id"]: self.toggle_channel_visibility(cid, state)
                )
                layout.addWidget(cb)

                # Color indicator
                color_label = QLabel()
                color_label.setFixedSize(16, 16)
                color_label.setStyleSheet(f"""
                    background-color: {channel['color']};
                    border: 1px solid #000;
                    border-radius: 3px;
                """)
                layout.addWidget(color_label)

                # Channel name
                name_label = QLabel(channel["display_name"])
                name_label.setStyleSheet("font-size: 12px;")
                layout.addWidget(name_label)
                layout.addStretch()

                # Edit button
                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon.fromTheme("document-edit"))
                edit_btn = QPushButton("✏️")  # Unicode pencil character
                edit_btn.setStyleSheet("font-size: 14px; padding: 0px;")
                edit_btn.setFixedSize(24, 24)
                edit_btn.setFixedSize(24, 24)
                edit_btn.clicked.connect(
                    partial(self.edit_channel, channel["id"])
                )
                layout.addWidget(edit_btn)

                item.setSizeHint(widget.sizeHint())
                self.channel_list.addItem(item)
                self.channel_list.setItemWidget(item, widget)

                # Store references
                self.graph_items[channel["id"]] = {
                    "curve": curve,
                    "config": channel,
                    "checkbox": cb
                }

        self.start_btn.setEnabled(True)

    def create_channel_widget(self, channel):
        """Helper method to create channel widget"""
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)

        # Visibility checkbox
        cb = QCheckBox()
        cb.setChecked(channel["visible"])
        cb.stateChanged.connect(partial(self.toggle_channel_visibility, channel["id"]))
        layout.addWidget(cb)

        # Color indicator
        color_label = QLabel()
        color_label.setFixedSize(16, 16)
        color_label.setStyleSheet(f"""
            background-color: {channel['color']};
            border: 1px solid #000;
            border-radius: 3px;
        """)
        layout.addWidget(color_label)

        # Channel name
        name_label = QLabel(channel["display_name"])
        name_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(name_label)
        layout.addStretch()

        # Edit button
        edit_btn = QPushButton()
        edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        edit_btn.setFixedSize(24, 24)
        edit_btn.clicked.connect(partial(self.edit_channel, channel["id"]))
        layout.addWidget(edit_btn)

        item.setSizeHint(widget.sizeHint())
        return item, widget, cb

    def toggle_module_visibility(self, module_name, state):
        """Toggle visibility for all channels in a module"""
        if module_name not in self.module_widgets:
            return

        # Update all channels in module
        any_visible = False
        for channel_id in self.module_widgets[module_name]['channels']:
            if channel_id in self.graph_items:
                self.graph_items[channel_id]["curve"].setVisible(state)
                self.graph_items[channel_id]["checkbox"].setChecked(state)
                self.graph_items[channel_id]["config"]["visible"] = state
                any_visible = any_visible or state

        # Update module checkbox without triggering signal
        self.module_widgets[module_name]['checkbox'].blockSignals(True)
        self.module_widgets[module_name]['checkbox'].setChecked(any_visible)
        self.module_widgets[module_name]['checkbox'].blockSignals(False)

        # Save configuration
        self.save_config()

    def edit_channel(self, channel_id):
        """Edit channel configuration"""
        if channel_id not in self.graph_items:
            return

        dialog = ChannelConfigDialog(self.graph_items[channel_id]["config"], self)
        if dialog.exec() == QDialog.Accepted:
            new_config = dialog.get_config()
            self.graph_items[channel_id]["config"].update(new_config)
            self.graph_items[channel_id]["checkbox"].setChecked(new_config["visible"])
            self.graph_items[channel_id]["curve"].setData(
                name=new_config["display_name"],
                pen=pg.mkPen(color=new_config["color"], width=2)
            )
            self.save_config()
            self.update_display()

    def start_measurement(self):
        """Start acquisition"""
        self.scan_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        QMessageBox.information(self, "Info", "Measurement started (simulation)")

    def stop_measurement(self):
        """Stop acquisition"""
        self.scan_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "Info", "Measurement stopped (simulation)")
