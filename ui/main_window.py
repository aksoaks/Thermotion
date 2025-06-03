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
                              QFrame, QSizePolicy,QInputDialog)
from PySide6.QtCore import Qt, Signal, QSize, QThread, QTimer
from PySide6.QtGui import QColor, QIcon, QFont, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError

from ui.dialogs import ChannelConfigDialog, DeviceScannerDialog
from ui.widgets import ChannelListWidget
from utils.style import MAIN_WINDOW_STYLE
from acquisition.acquisition_worker import AcquisitionWorker
import numpy as np
from nidaqmx.system import System

CONFIG_FILE = "config.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        icon_path = "c:/user/SF66405/Code/Python/cDAQ/icon.ico"
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
        self.acquisition_thread = None        
        self.load_config()
        self.check_devices_online()
    
        if self.config.get("devices"):
            self.update_display()
            self.check_devices_online()  # Ajoutez cette ligne

        self.worker = None
        self.worker_thread = None

        self.device_poll_timer = QTimer(self)
        self.device_poll_timer.setInterval(3000)  # Toutes les 3 secondes
        self.device_poll_timer.timeout.connect(self.check_device_status)
        self.device_poll_timer.start()
        self.acquisition_thread = None

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        # Graph Area
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Temperature', 'degC')
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

        self.scan_btn = QPushButton("Configure")
        self.scan_btn.clicked.connect(self.configure_devices)
        btn_layout.addWidget(self.scan_btn)

        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_acquisition)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        self.stop_btn.clicked.connect(self.stop_acquisition)
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

    def toggle_channel_visibility(self, channel_id, state):
        """Afficher ou masquer une courbe en fonction de la checkbox"""
        if channel_id in self.graph_items:
            visible = bool(state)
            self.graph_items[channel_id]["curve"].setVisible(visible)
            self.graph_items[channel_id]["config"]["visible"] = visible
            self.save_config()

    def check_devices_online(self):
        try:
            system = nidaqmx.system.System.local()
            online_device_names = [d.name for d in system.devices]

            for device_name, device_info in self.config.get("devices", {}).items():
                display_name = device_info.get("display_name", device_name)
                is_online = device_name in online_device_names

                for i in range(self.channel_list.count()):
                    item = self.channel_list.item(i)
                    widget = self.channel_list.itemWidget(item)
                    if widget:
                        layout = widget.layout()
                        if layout:
                            for j in range(layout.count()):
                                child = layout.itemAt(j).widget()
                                if isinstance(child, QLabel) and display_name in child.text():
                                    # Supprime ancien label
                                    text_base = display_name.split(" (offline)")[0]
                                    child.setText(text_base + (" (offline)" if not is_online else ""))
                                    child.setStyleSheet("color: red;" if not is_online else "")
                                    break
        except Exception as e:
            print(f"Device check error: {str(e)}")


    def save_config(self):
        """Save config to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not save config:\n{str(e)}")

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
            if not device_cfg.get("enabled", True):
                continue  # ❌ Ignorer module désactivé

            module_name = device_cfg.get("display_name", device_name)

            if module_name not in modules:
                modules[module_name] = {
                    "device_name": device_name,
                    "channels": []
                }

            # Add simulated channels (replace with real channels)
            for channel_id, channel_data in device_cfg.get("channels", {}).items():
                if not channel_data.get("enabled", True):
                    continue  # ❌ Ignorer canal désactivé
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
                partial(self.toggle_module_visibility, module_name)
            )
            header_layout.addWidget(module_cb)

            # Wrapper layout pour le texte + indicateur
            status_layout = QHBoxLayout()
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setSpacing(5)

            # Module name label
            name_label = QLabel(module_name)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("""
                font-weight: bold;
                font-size: 16px;
                color: white;
                padding: 2px;
            """)

            # Round status indicator (green = online, red = offline)
            status_indicator = QLabel()
            status_indicator.setFixedSize(12, 12)
            status_color = "#2ecc71" if device_cfg.get("online", True) else "#e74c3c"
            status_indicator.setStyleSheet(f"""
                background-color: {status_color};
                border-radius: 6px;
                border: 1px solid #333;
            """)

            # Ajouter les éléments à droite du nom
            status_layout.addWidget(name_label, 1)  # Stretchable
            status_layout.addWidget(status_indicator, 0, Qt.AlignRight)

            # Wrapper widget pour status layout
            status_widget = QWidget()
            status_widget.setLayout(status_layout)

            header_layout.addWidget(status_widget, 1)  # Stretchable


            # 🖊️ Edit button for module name
            edit_btn = QPushButton()
            edit_icon_path = os.path.join(os.path.dirname(__file__), "../resources/edit_white.png")
            edit_btn.setIcon(QIcon(edit_icon_path))
            edit_btn.setIconSize(QSize(16, 16))
            edit_btn.setStyleSheet("background-color: transparent; border: none;")
            edit_btn.setFixedSize(24, 24)
            edit_btn.clicked.connect(partial(self.edit_module_name, module_name))
            header_layout.addWidget(edit_btn)

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
                    pen=pg.mkPen(color=channel["color"].strip(), width=2)
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
                edit_icon_path = os.path.join(os.path.dirname(__file__), "../resources/edit_white.png")
                edit_btn.setIcon(QIcon(edit_icon_path))
                edit_btn.setIconSize(QSize(16, 16))
                edit_btn.setStyleSheet("background-color: transparent; border: none;")
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

        # Pass a copy to avoid modifying config before confirmation
        original_config = self.graph_items[channel_id]["config"].copy()
        dialog = ChannelConfigDialog(original_config, self)

        if dialog.exec() == QDialog.Accepted:
            new_config = dialog.get_config()

            # ✅ Update in self.config
            for device_name, device in self.config.get("devices", {}).items():
                if channel_id in device.get("channels", {}):
                    device["channels"][channel_id].update(new_config)
                    break

            self.save_config()
            self.update_display()

    def stop_measurement(self):
        """Stop acquisition"""
        self.scan_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "Info", "Measurement stopped (simulation)")

    def update_config_and_refresh_channels(self, new_config):
        self.config = new_config
        self.save_config()
        self.update_display()  # ✅ rafraîchit l’affichage     

    def configure_devices(self):
        dialog = DeviceScannerDialog(self, existing_config=self.config)
        dialog.config_updated.connect(self.update_config_and_refresh_channels)
        dialog.exec()

    def edit_module_name(self, module_name):
        text, ok = QInputDialog.getText(self, "Edit Module Name", "New name:", QLineEdit.Normal, module_name)
        if ok and text:
            # Trouver et mettre à jour le nom dans config
            for device_name, device in self.config["devices"].items():
                if device.get("display_name") == module_name:
                    device["display_name"] = text
                    break
            self.save_config()
            self.update_display()

    def start_acquisition(self):
        if not self.start_btn.isEnabled():
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        if self.acquisition_thread and self.acquisition_thread.isRunning():
            print("[DEBUG] Thread déjà actif → arrêt")
            self.stop_acquisition()

        self.worker = AcquisitionWorker(self.config)
        self.acquisition_thread = QThread()

        self.worker.moveToThread(self.acquisition_thread)

        self.worker.new_data.connect(self.handle_new_data)
        self.worker.finished.connect(self.acquisition_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.acquisition_thread.finished.connect(self.acquisition_thread.deleteLater)

        self.acquisition_thread.started.connect(self.worker.start)
        self.acquisition_thread.start()

        QTimer.singleShot(500, lambda: self.stop_btn.setEnabled(True))


    def stop_acquisition(self):
        if self.worker:
            self.worker.stop()
            # Do NOT set self.worker = None immediately
        if self.acquisition_thread:
            self.acquisition_thread.quit()
            self.acquisition_thread.wait()

        self.worker = None
        self.acquisition_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def handle_new_data(self, data):
        for channel_id, value in data.items():
            curve = self.graph_items.get(channel_id, {}).get("curve")
            config = self.graph_items.get(channel_id, {}).get("config")

            if curve and isinstance(value, (int, float)):
                curve.setData([0, 1, 2, 3, 4], [value] * 5)

                # ➕ Met à jour le nom avec la température
                new_label = f"{config['display_name']} : {value:.1f}°C"

                # 🔍 Mise à jour du QLabel correspondant dans la liste
                item_count = self.channel_list.count()
                for i in range(item_count):
                    item = self.channel_list.item(i)
                    widget = self.channel_list.itemWidget(item)
                    if widget:
                        labels = widget.findChildren(QLabel)
                        for label in labels:
                            if label.text().startswith(config['display_name']):
                                label.setText(new_label)
                                break  # 🛑 On a trouvé le bon QLabel, on sort


    def update_graph(self, data):
        for channel_id, value in data.items():
            if channel_id in self.graph_items:
                curve = self.graph_items[channel_id]["curve"]
                # ⚠️ À adapter pour stocker et faire défiler les valeurs
                curve.setData([0, 1, 2, 3, 4], [value]*5)

    def check_device_status(self):
        try:
            from nidaqmx.system import System
            system = System.local()
            connected_devices = set(dev.name for dev in system.devices)

            updated = False
            for device_name, device_cfg in self.config.get("devices", {}).items():
                previous = device_cfg.get("online", True)
                now = device_name in connected_devices

                if previous != now:
                    device_cfg["online"] = now
                    updated = True
                    status = "connecté" if now else "déconnecté"
                    print(f"[INFO] {device_name} est maintenant {status}")
                    self.show_status_message(f"{device_name} est maintenant {status}")

            if updated:
                self.update_display()

        except Exception as e:
            print(f"[ERROR] Failed to check device status: {e}")


    def closeEvent(self, event):
        print("[DEBUG] Fermeture de l'application...")
        self.stop_acquisition()
        event.accept()

    def show_status_message(self, message: str, duration_ms: int = 3000):
        self.statusBar().showMessage(message, duration_ms)