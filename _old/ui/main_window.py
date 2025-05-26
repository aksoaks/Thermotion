from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QFormLayout, QScrollArea,
    QFrame, QLineEdit, QMessageBox, QSizePolicy,
    QDialog, QColorDialog, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QFont, QPixmap
import pyqtgraph as pg
import nidaqmx.system
from nidaqmx.errors import DaqError

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermotion DAQ")
        self.setGeometry(100, 100, 1200, 800)
        
        # Variables comme dans l'ancien script
        self.devices = []
        self.config = {}
        self.active_channels = []
        self.module_widgets = {}
        
        # Initialisation UI identique
        self.init_identical_ui()
        
        # Premier scan
        self.scan_devices()

    def init_identical_ui(self):
        """Reproduit exactement l'UI de l'ancien script"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # --- Partie gauche (identique) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # Module list
        self.module_list = QListWidget()
        self.module_list.itemClicked.connect(self.on_module_selected)
        left_layout.addWidget(QLabel("Modules:"))
        left_layout.addWidget(self.module_list)
        
        # Bouton scan
        self.scan_btn = QPushButton("Scan Devices")
        self.scan_btn.clicked.connect(self.scan_devices)
        left_layout.addWidget(self.scan_btn)
        
        # Channel list
        self.channel_list = QListWidget()
        self.channel_list.itemDoubleClicked.connect(self.on_channel_selected)
        left_layout.addWidget(QLabel("Channels:"))
        left_layout.addWidget(self.channel_list)
        
        main_layout.addWidget(left_panel)
        
        # --- Partie centrale (identique) ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        main_layout.addWidget(self.plot_widget)
        
        # --- Partie droite (identique) ---
        right_panel = QScrollArea()
        right_panel.setFixedWidth(300)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        
        # Configuration group
        config_group = QGroupBox("Channel Config")
        self.config_form = QFormLayout()
        
        # Champs de configuration
        self.name_edit = QLineEdit()
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(50, 25)
        self.active_check = QCheckBox("Active")
        
        self.config_form.addRow("Name:", self.name_edit)
        self.config_form.addRow("Color:", self.color_btn)
        self.config_form.addRow(self.active_check)
        
        config_group.setLayout(self.config_form)
        right_layout.addWidget(config_group)
        
        # Boutons
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_config)
        right_layout.addWidget(self.apply_btn)
        
        right_panel.setWidget(right_content)
        main_layout.addWidget(right_panel)

    def scan_devices(self):
        """Même implémentation que dans l'ancien script"""
        try:
            system = nidaqmx.system.System.local()
            self.devices = [d for d in system.devices if "Mod" in d.name]
            
            self.module_list.clear()
            for device in self.devices:
                self.module_list.addItem(device.name)
                
        except DaqError as e:
            print(f"DAQmx Error: {str(e)}")

    def on_module_selected(self, item):
        """Gère la sélection d'un module (copié de l'ancien script)"""
        self.channel_list.clear()
        device_name = item.text()
        
        try:
            # Trouve le device correspondant
            device = next(d for d in self.devices if d.name == device_name)
            
            # Récupère les canaux physiques
            channels = device.ai_physical_chans
            
            # Ajoute chaque canal à la liste
            for ch in channels:
                channel_item = QListWidgetItem(ch.name.split('/')[-1])
                channel_item.setData(Qt.UserRole, ch.name)  # Stocke le nom complet
                self.channel_list.addItem(channel_item)
                
        except (StopIteration, DaqError) as e:
            print(f"Error loading channels: {str(e)}")
            QMessageBox.warning(self, "Error", f"Could not load channels:\n{str(e)}") 

    def on_channel_selected(self, item):
        """Gère la sélection d'un canal (copié de l'ancien script)"""
        channel_name = item.data(Qt.UserRole)
        
        # Configure le panneau droit avec les infos du canal
        self.name_edit.setText(channel_name.split('/')[-1])
        
        # Génère une couleur basée sur le hash du nom
        color = "#{:06x}".format(hash(channel_name) % 0xffffff)
        self.color_btn.setStyleSheet(f"background-color: {color};")
        
        # Active par défaut
        self.active_check.setChecked(True)
        
        # Stocke le canal courant
        self.current_channel = channel_name      

    def apply_config(self):
        """Applique la configuration (copié de l'ancien script)"""
        if not hasattr(self, 'current_channel') or not self.current_channel:
            return
            
        # Met à jour la configuration
        channel_config = {
            "display_name": self.name_edit.text(),
            "color": self.color_btn.styleSheet().split(':')[1].split(';')[0],
            "active": self.active_check.isChecked()
        }
        
        # Sauvegarde dans la config globale
        device_name = self.current_channel.split('/')[0]
        if device_name not in self.config:
            self.config[device_name] = {"channels": {}}
            
        self.config[device_name]["channels"][self.current_channel] = channel_config
        
        # Met à jour l'affichage
        self.update_display()
        
        # Sauvegarde dans le fichier
        self.save_config()