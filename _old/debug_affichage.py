import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QDialog, QLineEdit, QColorDialog, QListWidget,
                              QListWidgetItem, QCheckBox, QScrollArea, QGroupBox, QMessageBox,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QIcon, QFont, QIcon, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError
from functools import partial

CONFIG_FILE = "thermotion_config.json"

class ChannelConfigDialog(QDialog):
    def __init__(self, channel_data, parent=None):
        super().__init__(parent)
        self.channel_data = channel_data
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setRange(xRange=[0, 10], yRange=[0, 100], padding=0)
        self.plot_widget.enableAutoRange(axis='y', enable=False)
        self.setWindowTitle("Channel Settings")
        self.setFixedSize(400, 300)
        self.setStyleSheet("font-size: 12px;")
                
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
        """Sauvegarde la config et met à jour l'interface"""
        # 1. Sauvegarde la configuration
        self.save_config()
        self.config = self.load_config()
        
        # 3. Met à jour les vues
        self.update_channel_list()
        self.update_active_channels()  # Maintenant sécurisé
        
        # 4. Prépare et émet la config
        config_to_emit = {
            "version": 2,
            "devices": {
                dev.name: {
                    "channels": {ch.name: {"active": True} for ch in dev.ai_physical_chans}
                } for dev in self.devices
            }
        }
        self.config_updated.emit(config_to_emit)
    
    def update_active_channels(self):
        """Met à jour la QListWidget des canaux actifs"""
        self.active_channels_list.clear()
        
        # Exemple de structure attendue dans self.config:
        # {"modules": [{"name": "Mod1", "channels": [{"name": "ch1", "active": True}]}]}
        for module in self.config.get('modules', []):
            for channel in module.get('channels', []):
                if channel.get('active', False):
                    item = QListWidgetItem(f"{module['name']}/{channel['name']}")
                    self.active_channels_list.addItem(item)

    def get_device_channels(self, device):
        """Récupère tous les canaux physiques du device"""
        channels = {}
        try:
            for ch in device.ai_physical_chans:
                channel_id = ch.name
                channels[channel_id] = {
                    "display_name": channel_id.split('/')[-1],
                    "color": "#{:06x}".format(hash(channel_id) % 0xffffff),
                    "visible": True
                }
        except Exception as e:
            print(f"Error reading channels: {str(e)}")
        return channels

    def retry_detection(self):
        """Relance la détection des appareils"""
        try:
            # Nettoyer complètement l'interface avant rechargement
            for i in reversed(range(self.layout().count())):
                widget = self.layout().itemAt(i).widget()
                if widget:
                    widget.setParent(None)
            
            self.devices = self.detect_devices()
            self.init_ui()  # Reconstruit complètement l'interface
            
            if not self.devices:
                QMessageBox.information(self, "Info", "No devices found after rescan")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Rescan failed:\n{str(e)}")

class MainWindow(QMainWindow):
    config_updated = Signal(dict)  # Déclaration du signal avec PySide6

    def __init__(self):
        super().__init__()
        icon_path = os.path.join(os.path.dirname(__file__), "icon.jpg")
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
        if hasattr(self, 'config') and self.config.get("devices"):
            self.update_display()
            QTimer.singleShot(1000, self.check_devices_online)  # Délai pour laisser l'UI s'initialiser
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_devices_online)
        self.check_timer.start(30000)  # 30 secondes
        self.config_updated.connect(self.handle_config_update)

    def update_active_channels(self):
        """Met à jour la liste des canaux actifs à partir de la configuration"""
        if not hasattr(self, 'active_channels_list'):
            return  # Si le widget n'existe pas encore
        
        self.active_channels_list.clear()
        
        # Structure attendue dans config:
        # {"modules": [{"name": "mod1", "channels": [{"name": "ch1", "active": True}]}]}
        for module in self.config.get('modules', []):
            for channel in module.get('channels', []):
                if channel.get('active', False):
                    item_text = f"{module['name']}/{channel['name']}"
                    self.active_channels_list.addItem(item_text)

    def handle_config_update(self, config):
        """Gère les mises à jour de configuration"""
        print("Configuration reçue:", config)
        # Traitement de la nouvelle config si besoin

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        # Init channel List
        self.active_channels_list = QListWidget()
        self.active_channels_list.setMaximumWidth(200)
        
        # Graph Area
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Temperature', 'degC')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        layout.addWidget(self.plot_widget, 75)
        
        # Control Panel
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # Title
        title = QLabel("Active Channels")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        control_layout.addWidget(title)
               
        # Buttons - DOIT ÊTRE AVANT update_display()
        btn_layout = QHBoxLayout()

        # Appel initial pour peupler la liste
        self.update_active_channels()  # Maintenant cette méthode existe
        
        self.scan_btn = QPushButton("Scan Devices")
        self.scan_btn.clicked.connect(self.scan_devices)
        btn_layout.addWidget(self.scan_btn)
        
        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)  # Désactivé par défaut
        self.start_btn.clicked.connect(self.start_measurement)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        btn_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(btn_layout)
        layout.addWidget(control_panel, 25)
        
        # Initialisation APRES création des boutons
        self.module_widgets = {}
        self.load_config()
        if hasattr(self, 'config') and self.config.get("devices"):
            self.update_display()
            QTimer.singleShot(1500, self.check_devices_online)

        self.update_active_channels()
        self.update_channel_list()
    
    def update_plot(self):
        self.plot_widget.setLimits(xMin=0, xMax=10)
        self.plot_widget.enableAutoRange(axis='x')

    def load_config(self):
        """Load config from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                if hasattr(self, 'start_btn'):  # Vérification de sécurité
                    self.update_display()
            except Exception as e:
                print(f"Could not load config: {str(e)}")  # Message plus précis
    
    def check_devices_online(self):
        """Check device connection status"""
        try:
            system = nidaqmx.system.System.local()
            connected_devices = {d.name for d in system.devices}  # Utilisation d'un set pour la performance
            
            for channel_id in self.graph_items:
                device_name = channel_id.split('/')[0]  # Extrait "cDAQ2Mod1" de "cDAQ2Mod1/ai0"
                if device_name not in connected_devices:
                    # Marquer comme offline
                    self.graph_items[channel_id]["offline"] = True
                    # Mettre à jour le style si nécessaire
        except Exception as e:
            print(f"Device check error: {str(e)}")
                    
        except Exception as e:
            print(f"Device check error: {str(e)}")

    def save_config(self):
        """Save config to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
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
        if not hasattr(self, 'channel_list'):
            print("Warning: channel_list not initialized yet")
            return
        self.channel_list.clear()

        self.plot_widget.clear()
        self.graph_items = {}
        
        if not hasattr(self, 'module_widgets'):
            self.module_widgets = {}

        if not self.config.get("devices"):
            self.start_btn.setEnabled(False)
            return

        # Organize channels by module
        modules = {}
        for device_name, device_cfg in self.config["devices"].items():
            module_name = device_cfg["display_name"]
            channels = device_cfg["channels"]  # Accès direct au dictionnaire
            
            for channel_id, channel_cfg in channels.items():  # Utilisez directement les clés
                self.graph_items[channel_id] = {
                    "curve": self.plot_widget.plot(
                        [], 
                        [],
                        pen=pg.mkPen(color=channel_cfg["color"], width=2),
                        name=channel_cfg["display_name"]
                    ),
                    "config": channel_cfg
                }

        # Add modules to display
        for i, (module_name, module_data) in enumerate(modules.items()):
            # Add separator for modules (except first one)
            if i > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator_item = QListWidgetItem()
                separator_item.setFlags(separator_item.flags() & ~Qt.ItemIsSelectable)
                separator_item.setSizeHint(QSize(0, 10))
                self.channel_list.addItem(separator_item)
                self.channel_list.setItemWidget(separator_item, separator)
            
            # Add module header with visibility control
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            
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
            name_label.setStyleSheet("font-weight: bold;")
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
                    pen=pg.mkPen(color=channel["color"], width=2),
                    name=channel["display_name"]
                )
                
                # Create list item
                item, widget, cb = self.create_channel_widget(channel)
                self.channel_list.addItem(item)
                self.channel_list.setItemWidget(item, widget)
                
                # Store references
                self.graph_items[channel["id"]] = {
                    "curve": curve,
                    "config": channel,
                    "checkbox": cb
                }
        
        self.start_btn.setEnabled(True)
        if hasattr(self, 'start_btn'):  # Vérification supplémentaire
            self.start_btn.setEnabled(bool(self.config.get("devices")))

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set default icon theme if not available
    if not QIcon.hasThemeIcon("document-edit"):
        QIcon.setThemeName("breeze")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())