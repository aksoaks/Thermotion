import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QDialog, QCheckBox, QLineEdit, 
                               QScrollArea, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
import pyqtgraph as pg

class DeviceConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Connection")
        self.setMinimumSize(600, 400)
        
        # Données simulées - à remplacer par votre détection réelle
        self.detected_interfaces = [
            {"name": "USB-4711", "channels": ["AI0", "AI1", "AI2", "AI3"]},
            {"name": "PCI-6289", "channels": ["AI0", "AI1", "AI2", "AI3", "AI4", "AI5"]}
        ]
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Message de détection
        detection_msg = QLabel(f"{len(self.detected_interfaces)} interface(s) detected")
        detection_msg.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(detection_msg)
        
        # Zone scrollable pour les interfaces
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Création des groupes pour chaque interface
        self.interface_widgets = []
        for i, interface in enumerate(self.detected_interfaces):
            group = QGroupBox(f"Interface {i+1}")
            group.setCheckable(True)
            group.setChecked(True)
            
            group_layout = QVBoxLayout()
            
            # Nom personnalisé de l'interface
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Display name:"))
            name_edit = QLineEdit(interface["name"])
            name_layout.addWidget(name_edit)
            group_layout.addLayout(name_layout)
            
            # Configuration des voies
            channels_group = QGroupBox("Channels Configuration")
            channels_layout = QVBoxLayout()
            
            self.channel_widgets = []
            for ch in interface["channels"]:
                ch_layout = QHBoxLayout()
                
                cb = QCheckBox(ch)
                cb.setChecked(True)
                
                rename_edit = QLineEdit(ch)
                rename_edit.setMaximumWidth(150)
                
                ch_layout.addWidget(cb)
                ch_layout.addWidget(QLabel("Display as:"))
                ch_layout.addWidget(rename_edit)
                ch_layout.addStretch()
                
                channels_layout.addLayout(ch_layout)
                self.channel_widgets.append((cb, rename_edit))
            
            channels_group.setLayout(channels_layout)
            group_layout.addWidget(channels_group)
            group.setLayout(group_layout)
            
            scroll_layout.addWidget(group)
            self.interface_widgets.append((group, name_edit, self.channel_widgets))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Boutons de validation
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_apply = QPushButton("Apply Configuration")
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_configuration(self):
        """Retourne la configuration sélectionnée"""
        config = []
        
        for group, name_edit, channel_widgets in self.interface_widgets:
            if group.isChecked():
                interface_cfg = {
                    "original_name": group.title().replace("Interface ", ""),
                    "display_name": name_edit.text(),
                    "channels": []
                }
                
                for cb, rename_edit in channel_widgets:
                    if cb.isChecked():
                        interface_cfg["channels"].append({
                            "original_id": cb.text(),
                            "display_name": rename_edit.text()
                        })
                
                if interface_cfg["channels"]:  # Ne garder que les interfaces avec au moins une voie active
                    config.append(interface_cfg)
        
        return config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermotion - Multichannel Measurement")
        self.setGeometry(100, 100, 1000, 700)
        
        self.active_config = []  # Stocke la configuration active
        self.graph_widgets = {}  # Dictionnaire des widgets graphiques
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect Device")
        self.connect_btn.clicked.connect(self.show_device_dialog)
        toolbar.addWidget(self.connect_btn)
        
        self.start_btn = QPushButton("Start Measurement")
        self.start_btn.setEnabled(False)
        toolbar.addWidget(self.start_btn)
        
        main_layout.addLayout(toolbar)
        
        # Zone graphique
        self.graph_area = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_area)
        main_layout.addWidget(self.graph_area)
        
        # Message par défaut
        self.default_message = QLabel("Please connect a device to begin measurement")
        self.default_message.setAlignment(Qt.AlignCenter)
        self.default_message.setStyleSheet("font-size: 16px; color: #666;")
        self.graph_layout.addWidget(self.default_message)
    
    def show_device_dialog(self):
        dialog = DeviceConfigDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.active_config = dialog.get_configuration()
            self.update_interface()
    
    def update_interface(self):
        """Met à jour l'interface en fonction de la configuration active"""
        # Nettoyer la zone graphique
        for i in reversed(range(self.graph_layout.count())): 
            self.graph_layout.itemAt(i).widget().setParent(None)
        
        if not self.active_config:
            self.graph_layout.addWidget(self.default_message)
            self.start_btn.setEnabled(False)
            return
        
        # Créer les graphiques pour chaque voie
        for interface in self.active_config:
            # Groupe pour l'interface
            group = QGroupBox(interface["display_name"])
            group_layout = QVBoxLayout()
            
            for channel in interface["channels"]:
                # Créer un widget graphique pour chaque voie
                pw = pg.PlotWidget(title=channel["display_name"])
                pw.plotItem.plot([0, 1, 2, 3, 4], [0, 1, 4, 9, 16])  # Données de test
                
                group_layout.addWidget(pw)
                self.graph_widgets[f"{interface['original_name']}_{channel['original_id']}"] = pw
            
            group.setLayout(group_layout)
            self.graph_layout.addWidget(group)
        
        self.start_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())