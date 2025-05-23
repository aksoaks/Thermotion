from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QPushButton, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt
import pyqtgraph as pg
from config.config_manager import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.init_ui()
        self.load_config()
        
        # Configuration initiale de la fenêtre
        self.setWindowTitle("Thermotion DAQ")
        self.setGeometry(100, 100, 1200, 800)

    def init_ui(self):
        """Réplique l'interface de debug_affichage.py"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal (horizontal)
        main_layout = QHBoxLayout(central_widget)
        
        # ------ Partie gauche : Liste des canaux ------
        left_panel = QWidget()
        left_panel.setMaximumWidth(250)
        left_layout = QVBoxLayout(left_panel)
        
        # Liste des canaux (comme dans l'ancienne version)
        self.channel_list = QListWidget()
        left_layout.addWidget(self.channel_list)
        
        # Boutons de contrôle
        btn_scan = QPushButton("Scan Devices")
        btn_scan.clicked.connect(self.scan_devices)
        left_layout.addWidget(btn_scan)
        
        main_layout.addWidget(left_panel)
        
        # ------ Partie centrale : Graphique ------
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        main_layout.addWidget(self.plot_widget, stretch=1)
        
        # ------ Partie droite : Configuration ------
        right_panel = QScrollArea()
        right_panel.setMaximumWidth(300)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        
        # Groupe pour la configuration (comme dans l'ancienne version)
        config_group = QGroupBox("Channel Configuration")
        self.config_layout = QVBoxLayout()
        config_group.setLayout(self.config_layout)
        right_layout.addWidget(config_group)
        
        right_panel.setWidget(right_content)
        main_layout.addWidget(right_panel)

    def load_config(self):
        """Charge la configuration et peuple l'interface"""
        # Implémente la même logique que dans l'ancien script
        pass

    def scan_devices(self):
        """Scan les appareils NI-DAQ comme avant"""
        # Implémente la même logique que dans l'ancien script
        print("Scanning devices...")