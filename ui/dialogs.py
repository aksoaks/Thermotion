import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QColorDialog, QCheckBox, QScrollArea, QWidget, QGroupBox, QMessageBox, QScrollArea,QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from functools import partial
import nidaqmx.system


class ChannelConfigDialog(QDialog):
    def __init__(self, channel_data, parent=None):
        super().__init__(parent)
        self.channel_data = channel_data
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

        # Thermocouple Type Selection
        thermo_layout = QHBoxLayout()
        thermo_layout.addWidget(QLabel("Thermocouple Type:"))

        self.thermo_combo = QComboBox()
        self.thermo_combo.addItems(["K", "T", "J", "E", "N", "R", "S", "B"])

        default_type = self.channel_data.get("thermocouple_type", "T")
        index = self.thermo_combo.findText(default_type)
        if index >= 0:
            self.thermo_combo.setCurrentIndex(index)

        thermo_layout.addWidget(self.thermo_combo)
        layout.addLayout(thermo_layout)

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
        
        # Scroll area
        self.scroll = QScrollArea()  # 👈 sauvegarde dans self
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)

        # Remonter automatiquement en haut après reconstruction
        self.scroll.verticalScrollBar().setValue(0)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_btn.styleSheet().split(':')[1].split(';')[0]))
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def get_config(self):
        return {
            "display_name": self.name_edit.text(),
            "color": self.color_btn.styleSheet().split(':')[1].split(';')[0].strip(),
            "visible": True,
            "thermocouple_type": self.thermo_combo.currentText()
        }

class DeviceScannerDialog(QDialog):
    config_updated = Signal(dict)

    def __init__(self, parent=None, existing_config=None):
        super().__init__(parent)
        self.setWindowTitle("Device Configuration")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog { font-size: 12px; }
            QGroupBox { font-size: 12px; font-weight: bold; }
        """)
        self.existing_config = existing_config or {}
        self.channel_custom_data = {}
        self.channel_labels = {}
        self.channel_checkboxes = {}
        self.main_layout = QVBoxLayout(self)
        self.devices = self.detect_devices()
        self.init_ui()

    def detect_devices(self):
        try:
            system = nidaqmx.system.System.local()
            return [d for d in system.devices if "Mod" in d.name]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Device detection failed:\n{str(e)}")
            return []

    def init_ui(self):
        layout = self.main_layout
        # vider le layout explicitement
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.module_channels = {}
        if not self.devices:
            layout.addWidget(QLabel("No NI-DAQmx modules detected"))
            retry_btn = QPushButton("Retry")
            retry_btn.clicked.connect(self.retry_detection)
            layout.addWidget(retry_btn)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        self.device_widgets = []

        self.module_channels = {}  # Initialise une fois en haut de init_ui()

        for device in self.devices:
            device_name = device.name
            self.module_channels[device_name] = []  # ✅ Init liste des canaux pour ce module

            mod_num = device.name.split("Mod")[1]
            chassis = device.name.split("Mod")[0] + "Chassis"
            online_devices = [d.name for d in nidaqmx.system.System.local().devices]
            is_online = device.name in online_devices

            display_name = f"{chassis} > Module {mod_num}"
            if not is_online:
                display_name += " (offline)"

            group = QGroupBox(display_name)
            group.setCheckable(True)
            group.setChecked(True)
            layout_inner = QVBoxLayout()

            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Module Name:"))
            saved_name = self.existing_config.get("devices", {}).get(device.name, {}).get("display_name", device.name)
            name_edit = QLineEdit(saved_name)
            name_edit.setStyleSheet("font-size: 12px;")
            name_layout.addWidget(name_edit)
            layout_inner.addLayout(name_layout)

            channels_group = QGroupBox("Channels")
            channels_group.setStyleSheet("font-size: 12px;")
            channels_layout = QVBoxLayout()

            try:
                channels = [c.name.split('/')[-1] for c in device.ai_physical_chans]
                for ch in sorted(channels):
                    channel_id = f"{device.name}/{ch}"

                    ch_config = {
                        "display_name": ch,
                        "color": "#{:06x}".format(hash(channel_id) % 0xffffff),
                        "visible": True
                    }

                    if device.name in self.existing_config.get("devices", {}):
                        ch_saved = self.existing_config["devices"][device.name]["channels"].get(channel_id)
                        if ch_saved:
                            ch_config.update(ch_saved)

                    self.channel_custom_data[channel_id] = ch_config
                    self.module_channels[device_name].append(channel_id)  # ✅ Ajout ici

                    ch_layout = QHBoxLayout()
                    cb = QCheckBox()
                    cb.setChecked(ch_config["visible"])
                    cb.stateChanged.connect(lambda state, cid=channel_id: self.set_channel_visibility(cid, state))
                    self.channel_checkboxes[channel_id] = cb
                    ch_layout.addWidget(cb)

                    label = QLabel(f"{ch}: {ch_config['display_name']}")
                    self.channel_labels[channel_id] = label
                    ch_layout.addWidget(label)
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

        toggle_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        unselect_all_btn = QPushButton("Disable All")
        select_all_btn.clicked.connect(lambda: self.set_all_visibility(True))
        unselect_all_btn.clicked.connect(lambda: self.set_all_visibility(False))
        toggle_layout.addWidget(select_all_btn)
        toggle_layout.addWidget(unselect_all_btn)
        layout.addLayout(toggle_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("font-size: 12px;")
        apply_btn.clicked.connect(self.apply_config)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("font-size: 12px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def edit_channel(self, device_name, channel_name):
        channel_id = f"{device_name}/{channel_name}"
        default_data = {
            "display_name": channel_name,
            "color": "#{:06x}".format(hash(channel_id) % 0xffffff),
            "visible": True
        }

        data = self.channel_custom_data.get(channel_id, default_data)
        dialog = ChannelConfigDialog(data, self)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.get_config()
            self.channel_custom_data[channel_id] = updated
            if channel_id in self.channel_labels:
                self.channel_labels[channel_id].setText(f"{channel_name}: {updated['display_name']}")

    def set_channel_visibility(self, channel_id, state):
        if channel_id in self.channel_custom_data:
            self.channel_custom_data[channel_id]["visible"] = bool(state)

    def set_all_visibility(self, visible):
        for group, _, device in self.device_widgets:
            group.setChecked(visible)
            device_name = device.name
            for ch in self.module_channels.get(device_name, []):
                cb = self.channel_checkboxes.get(ch)
                if cb:
                    cb.setChecked(visible)
                    self.channel_custom_data[ch]["visible"] = visible
                    

    def apply_config(self):
        config = {
            "version": 1,
            "devices": {}
        }

        for group, name_edit, device in self.device_widgets:
            device_name = device.name
            device_enabled = group.isChecked()

            device_entry = {
                "display_name": name_edit.text(),
                "enabled": device_enabled,  # ✅ on garde l'état du module
                "channels": {}
            }
            device_entry["online"] = True  # au moment du scan, on sait qu’il est connecté

            try:
                channels = [c.name.split('/')[-1] for c in device.ai_physical_chans]
                for ch in sorted(channels):
                    channel_id = f"{device_name}/{ch}"

                    ch_data = self.channel_custom_data.get(channel_id, {
                        "display_name": ch,
                        "color": "#{:06x}".format(hash(channel_id) % 0xffffff),
                        "visible": True,
                        "thermocouple_type": "T"  # ✅ par défaut
                    })

                    checkbox = self.channel_checkboxes.get(channel_id)
                    ch_data["enabled"] = checkbox.isChecked() if checkbox else True

                    device_entry["channels"][channel_id] = ch_data

            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Error collecting channels:\n{str(e)}")

            config["devices"][device_name] = device_entry

        self.config_updated.emit(config)
        self.accept()


    def retry_detection(self):
        self.devices = self.detect_devices()

        if not self.devices:
            self.show_no_device_message()
        else:
            self.init_ui()

    def show_no_device_message(self):
        # Nettoie la fenêtre
        layout = self.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

        # Message
        label = QLabel("No devices found.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Bouton Retry
        retry_btn = QPushButton("Retry")
        retry_btn.setFixedWidth(100)
        retry_btn.clicked.connect(self.retry_detection)
        layout.addWidget(retry_btn)
