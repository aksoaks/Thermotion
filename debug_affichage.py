import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QDialog, QCheckBox, QLineEdit, 
                               QScrollArea, QGroupBox, QMessageBox, QColorDialog, QListWidget,
                               QListWidgetItem, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError

# Chemin du fichier de configuration
CONFIG_FILE = "channel_config.json"

class ChannelEditDialog(QDialog):
    def __init__(self, channel_config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Configuration")
        self.setMinimumSize(400, 300)
        
        self.channel_config = channel_config or {
            "display_name": "New Channel",
            "color": "#FF0000",
            "visible": True
        }
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Nom du canal
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Channel name:"))
        self.name_edit = QLineEdit(self.channel_config["display_name"])
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Couleur
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(24, 24)
        self.color_btn.setStyleSheet(f"background-color: {self.channel_config['color']}; border: none;")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Visibilité
        self.visible_cb = QCheckBox("Visible")
        self.visible_cb.setChecked(self.channel_config["visible"])
        layout.addWidget(self.visible_cb)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.color_btn.styleSheet().split(':')[1].split(';')[0].strip()))
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: none;")
    
    def get_config(self):
        return {
            "display_name": self.name_edit.text(),
            "color": self.color_btn.styleSheet().split(':')[1].split(';')[0].strip(),
            "visible": self.visible_cb.isChecked()
        }

class DeviceConfigDialog(QDialog):
    config_saved = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Connection")
        self.setMinimumSize(800, 600)
        
        self.detected_interfaces = self.detect_devices()
        self.load_config()
        self.init_ui()
    
    def detect_devices(self):
        """Détection des appareils NI-DAQmx avec filtrage des modules seulement"""
        interfaces = []
        
        try:
            system = nidaqmx.system.System.local()
            
            for device in system.devices:
                if "Mod" not in device.name:
                    continue
                    
                try:
                    chassis_name = device.name.split("Mod")[0] + device.name.split("Mod")[1][0]
                    channels = [chan.name for chan in device.ai_physical_chans]
                    formatted_channels = [f"AI{ch.split('ai')[-1]}" for ch in channels if 'ai' in ch.lower()]
                    
                    interfaces.append({
                        "name": device.name,
                        "chassis": chassis_name,
                        "model": device.product_type,
                        "channels": formatted_channels,
                        "device_obj": device
                    })
                    
                except Exception as e:
                    print(f"Erreur lors de l'analyse de {device.name}: {str(e)}")
                    continue
                    
        except DaqError as e:
            QMessageBox.critical(self, "DAQmx Error", f"NI-DAQmx access error:\n{str(e)}")
            return []
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error:\n{str(e)}")
            return []
        
        return interfaces
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        self.saved_config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.saved_config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {str(e)}")
    
    def save_config(self, config):
        """Sauvegarde la configuration dans un fichier JSON"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            self.config_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save config: {str(e)}")
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        if not self.detected_interfaces:
            layout.addWidget(QLabel("No NI-DAQmx modules found. Please check connections."))
            btn_retry = QPushButton("Retry Detection")
            btn_retry.clicked.connect(self.retry_detection)
            layout.addWidget(btn_retry)
            self.setLayout(layout)
            return
        
        # Message de détection
        detection_msg = QLabel(f"{len(self.detected_interfaces)} NI-DAQmx module(s) detected")
        detection_msg.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(detection_msg)
        
        # Zone scrollable pour les interfaces
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Création des groupes pour chaque interface
        self.interface_widgets = []
        for interface in self.detected_interfaces:
            group = QGroupBox(f"{interface['chassis']} > {interface['name']} ({interface['model']})")
            group.setCheckable(True)
            group.setChecked(True)
            
            group_layout = QVBoxLayout()
            
            # Configuration des voies
            channels_group = QGroupBox("Analog Input Channels Configuration")
            channels_layout = QVBoxLayout()
            
            self.channel_widgets = []
            colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF']
            
            for i, ch in enumerate(sorted(interface['channels'], key=lambda x: int(x[2:]))):
                # Récupération de la config sauvegardée si elle existe
                channel_id = f"{interface['name']}/{ch}"
                saved_channel = self.saved_config.get(channel_id, {})
                
                ch_layout = QHBoxLayout()
                
                # Case à cocher
                cb = QCheckBox(ch)
                cb.setChecked(True)
                
                # Nom personnalisé
                default_name = saved_channel.get("display_name", f"{interface['name']}_{ch}")
                name_edit = QLineEdit(default_name)
                name_edit.setMaximumWidth(200)
                
                # Sélecteur de couleur
                color_btn = QPushButton()
                color_btn.setFixedSize(24, 24)
                default_color = saved_channel.get("color", colors[i % len(colors)])
                color_btn.setStyleSheet(f"background-color: {default_color}; border: none;")
                
                def make_color_callback(btn):
                    def callback():
                        color = QColorDialog.getColor(QColor(btn.styleSheet().split(':')[1].split(';')[0].strip()))
                        if color.isValid():
                            btn.setStyleSheet(f"background-color: {color.name()}; border: none;")
                    return callback
                
                color_btn.clicked.connect(make_color_callback(color_btn))
                
                ch_layout.addWidget(cb)
                ch_layout.addWidget(QLabel("Name:"))
                ch_layout.addWidget(name_edit)
                ch_layout.addWidget(QLabel("Color:"))
                ch_layout.addWidget(color_btn)
                ch_layout.addStretch()
                
                channels_layout.addLayout(ch_layout)
                self.channel_widgets.append((cb, name_edit, color_btn, ch))
            
            channels_group.setLayout(channels_layout)
            group_layout.addWidget(channels_group)
            group.setLayout(group_layout)
            
            scroll_layout.addWidget(group)
            self.interface_widgets.append((group, self.channel_widgets, interface))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Boutons de validation
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_apply = QPushButton("Apply Configuration")
        btn_apply.clicked.connect(self.apply_config)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def apply_config(self):
        """Applique la configuration et sauvegarde"""
        config = self.get_configuration()
        self.save_config(config)
        self.accept()
    
    def retry_detection(self):
        """Relance la détection des appareils"""
        self.detected_interfaces = self.detect_devices()
        for i in reversed(range(self.layout().count())): 
            self.layout().itemAt(i).widget().setParent(None)
        self.init_ui()
    
    def get_configuration(self):
        """Retourne la configuration complète"""
        config = {}
        
        for group, channel_widgets, interface in self.interface_widgets:
            if group.isChecked():
                for cb, name_edit, color_btn, original_ch in channel_widgets:
                    if cb.isChecked():
                        channel_id = f"{interface['name']}/{original_ch}"
                        config[channel_id] = {
                            "device_name": interface['name'],
                            "chassis_name": interface['chassis'],
                            "original_id": original_ch,
                            "display_name": name_edit.text(),
                            "color": color_btn.styleSheet().split(':')[1].split(';')[0].strip(),
                            "model": interface['model'],
                            "visible": True
                        }
        
        return config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermotion - NI-DAQmx Multichannel Measurement")
        self.setGeometry(100, 100, 1200, 800)
        
        self.active_config = {}
        self.graph_items = {}
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Partie graphique
        graph_container = QWidget()
        graph_layout = QVBoxLayout(graph_container)
        
        # Graphique principal
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Voltage', 'V')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        
        graph_layout.addWidget(self.plot_widget)
        
        # Partie contrôle
        control_container = QWidget()
        control_container.setMaximumWidth(250)
        control_layout = QVBoxLayout(control_container)
        
        # Titre
        control_layout.addWidget(QLabel("Channels Configuration"))
        
        # Liste des canaux
        self.channel_list = QListWidget()
        self.channel_list.itemClicked.connect(self.toggle_channel_visibility)
        control_layout.addWidget(self.channel_list)
        
        # Boutons
        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Devices")
        self.scan_btn.clicked.connect(self.show_device_dialog)
        btn_layout.addWidget(self.scan_btn)
        
        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        
        control_layout.addLayout(btn_layout)
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        
        # Ajout des deux parties à la fenêtre principale
        main_layout.addWidget(graph_container)
        main_layout.addWidget(separator)
        main_layout.addWidget(control_container)
    
    def load_config(self):
        """Charge la configuration depuis le fichier"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.active_config = json.load(f)
                    self.update_interface()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load config: {str(e)}")
    
    def show_device_dialog(self):
        dialog = DeviceConfigDialog(self)
        dialog.config_saved.connect(self.load_config)
        dialog.exec()
    
    def update_interface(self):
        """Met à jour l'interface avec la configuration active"""
        # Nettoyer les anciens éléments
        self.plot_widget.clear()
        self.channel_list.clear()
        self.graph_items = {}
        
        if not self.active_config:
            self.start_btn.setEnabled(False)
            return
        
        # Créer les courbes et les éléments de la liste
        for channel_id, config in self.active_config.items():
            # Création de la courbe
            curve = self.plot_widget.plot([], [], name=config["display_name"], 
                                        pen=pg.mkPen(color=config["color"], width=2))
            
            # Création de l'item dans la liste
            item = QListWidgetItem(config["display_name"])
            item.setData(Qt.UserRole, channel_id)
            
            # Case à cocher pour la visibilité
            item.setCheckState(Qt.Checked if config.get("visible", True) else Qt.Unchecked)
            
            # Bouton d'édition
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            
            color_label = QLabel()
            color_label.setFixedSize(16, 16)
            color_label.setStyleSheet(f"background-color: {config['color']}; border: 1px solid #000;")
            
            edit_btn = QPushButton()
            edit_btn.setIcon(QIcon.fromTheme("document-edit"))
            edit_btn.setFixedSize(24, 24)
            edit_btn.clicked.connect(lambda _, cid=channel_id: self.edit_channel(cid))
            
            layout.addWidget(color_label)
            layout.addWidget(QLabel(config["display_name"]))
            layout.addStretch()
            layout.addWidget(edit_btn)
            
            item.setSizeHint(widget.sizeHint())
            
            self.channel_list.addItem(item)
            self.channel_list.setItemWidget(item, widget)
            
            # Stockage des références
            self.graph_items[channel_id] = {
                "curve": curve,
                "config": config,
                "visible": config.get("visible", True),
                "data": {"x": [], "y": []}
            }
        
        self.start_btn.setEnabled(True)
    
    def toggle_channel_visibility(self, item):
        """Active/désactive la visibilité d'un canal"""
        channel_id = item.data(Qt.UserRole)
        is_visible = item.checkState() == Qt.Checked
        
        if channel_id in self.graph_items:
            self.graph_items[channel_id]["curve"].setVisible(is_visible)
            self.graph_items[channel_id]["visible"] = is_visible
    
    def edit_channel(self, channel_id):
        """Ouvre la fenêtre d'édition d'un canal"""
        if channel_id not in self.active_config:
            return
        
        # Création de la fenêtre d'édition
        dialog = ChannelEditDialog(self.active_config[channel_id], self)
        if dialog.exec() == QDialog.Accepted:
            # Mise à jour de la configuration
            new_config = dialog.get_config()
            self.active_config[channel_id].update(new_config)
            
            # Sauvegarde
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(self.active_config, f, indent=4)
                
                # Mise à jour de l'interface
                self.update_interface()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save config: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Création d'une icône de stylo si elle n'existe pas
    if not QIcon.hasThemeIcon("document-edit"):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        QIcon.setThemeName("breeze")  # Essaye d'utiliser un thème qui a l'icône
    
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())