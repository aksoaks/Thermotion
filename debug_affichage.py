import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QDialog, 
                              QLineEdit, QColorDialog, QListWidget, QListWidgetItem, 
                              QCheckBox, QScrollArea, QGroupBox, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError
from functools import partial

CONFIG_FILE = "thermotion_config.json"

class ChannelConfigDialog(QDialog):
    def __init__(self, channel_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Settings")
        self.setFixedSize(400, 300)
        
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
        
        # Visibility
        self.visible_cb = QCheckBox("Visible")
        self.visible_cb.setChecked(self.channel_data.get("visible", True))
        layout.addWidget(self.visible_cb)
        
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
            "visible": self.visible_cb.isChecked()
        }

class DeviceScannerDialog(QDialog):
    config_updated = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Configuration")
        self.setMinimumSize(800, 600)
        
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
            name_layout.addWidget(name_edit)
            layout_inner.addLayout(name_layout)
            
            # Channels
            channels_group = QGroupBox("Channels")
            channels_layout = QVBoxLayout()
            
            try:
                channels = [c.name.split('/')[-1] for c in device.ai_physical_chans]
                for i, ch in enumerate(sorted(channels)):
                    ch_layout = QHBoxLayout()
                    
                    ch_layout.addWidget(QLabel(ch))
                    ch_layout.addStretch()
                    
                    edit_btn = QPushButton("Edit")
                    edit_btn.setFixedWidth(80)
                    edit_btn.clicked.connect(lambda _, d=device.name, c=ch: self.edit_channel(d, c))
                    
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
        apply_btn.clicked.connect(self.apply_config)
        btn_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def edit_channel(self, device_name, channel_name):
        """Edit individual channel settings"""
        channel_id = f"{device_name}/{channel_name}"
        channel_data = self.load_channel_config(channel_id)
        
        dialog = ChannelConfigDialog(channel_data, self)
        if dialog.exec() == QDialog.Accepted:
            self.save_channel_config(channel_id, dialog.get_config())
    
    def load_channel_config(self, channel_id):
        """Load channel config with defaults"""
        default_color = "#{:06x}".format(hash(channel_id) % 0xffffff)
        return {
            "display_name": channel_id.split('/')[-1],
            "color": default_color,
            "visible": True
        }
    
    def save_channel_config(self, channel_id, config):
        """Save channel config (would be saved to JSON later)"""
        print(f"Saving config for {channel_id}: {config}")
        # In full implementation, this would update the complete config
    
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
                    "channels": {}  # Would be populated with channel data
                }
        
        self.config_updated.emit(config)
        self.accept()
    
    def retry_detection(self):
        """Retry device detection"""
        self.devices = self.detect_devices()
        self.init_ui()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermotion")
        self.setGeometry(100, 100, 1200, 800)
        
        self.config = {}
        self.init_ui()
        self.load_config()
    
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
        self.channel_list = QListWidget()
        self.channel_list.itemClicked.connect(self.toggle_channel)
        control_layout.addWidget(self.channel_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        scan_btn = QPushButton("Scan Devices")
        scan_btn.clicked.connect(self.scan_devices)
        btn_layout.addWidget(scan_btn)
        
        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        
        control_layout.addLayout(btn_layout)
        layout.addWidget(control_panel, 25)  # 25% width
    
    def scan_devices(self):
        """Open device scanner dialog"""
        dialog = DeviceScannerDialog(self)
        dialog.config_updated.connect(self.update_config)
        dialog.exec()
    
    def update_config(self, new_config):
        """Update configuration"""
        self.config = new_config
        self.update_display()
    
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
    
    def update_display(self):
        """Update UI based on current config"""
        self.plot_widget.clear()
        self.channel_list.clear()
        
        if not self.config.get("devices"):
            return
        
        # Add test data (replace with real acquisition)
        for device_name, device_cfg in self.config["devices"].items():
            for i in range(4):  # Simulate 4 channels per device
                channel_id = f"{device_name}/ai{i}"
                color = "#{:06x}".format(hash(channel_id) % 0xffffff)
                
                # Create plot item
                curve = self.plot_widget.plot(
                    [0, 1, 2, 3, 4], 
                    [i, i+1, i+2, i+3, i+4],
                    name=f"{device_cfg['display_name']} Ch{i}",
                    pen=pg.mkPen(color=color, width=2)
                )
                
                # Add to channel list
                item = QListWidgetItem()
                widget = QWidget()
                item_layout = QHBoxLayout(widget)
                
                # Color indicator
                color_label = QLabel()
                color_label.setFixedSize(20, 20)
                color_label.setStyleSheet(f"background-color: {color}; border: 1px solid #000;")
                item_layout.addWidget(color_label)
                
                # Channel name
                item_layout.addWidget(QLabel(f"{device_cfg['display_name']} Ch{i}"))
                item_layout.addStretch()
                
                # Edit button
                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon.fromTheme("document-edit"))
                edit_btn.setFixedSize(24, 24)
                edit_btn.clicked.connect(lambda checked, c=channel_id: self.edit_channel(c))
                #Êedit_btn.clicked.connect(partial(self.edit_channel, channel_id))
                item_layout.addWidget(edit_btn)
                
                item.setSizeHint(widget.sizeHint())
                self.channel_list.addItem(item)
                self.channel_list.setItemWidget(item, widget)
        
        self.start_btn.setEnabled(True)
    
    def toggle_channel(self, item):
        """Toggle channel visibility"""
        # Implementation would toggle curve visibility
        pass
    
    def edit_channel(self, channel_id):
        """Edit channel configuration"""
        # Créer une couleur unique basée sur l'ID du canal
        color = "#{:06x}".format(hash(channel_id) % 0xffffff)
        
        # Ouvrir la boîte de dialogue avec les paramètres actuels
        dialog = ChannelConfigDialog({
            "display_name": channel_id.split('/')[-1],
            "color": color,
            "visible": True
        }, self)
        
        if dialog.exec() == QDialog.Accepted:
            print(f"Updated config for {channel_id}: {dialog.get_config()}")
                # Ici vous devriez:
                # 1. Mettre à jour self.config
                # 2. Sauvegarder dans le fichier JSON
                # 3. Actualiser l'affichage

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())