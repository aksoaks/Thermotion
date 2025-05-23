from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QListWidget)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.init_ui()
        self.load_initial_config()
        
        # Configuration de base de la fenêtre
        self.setWindowTitle("Thermotion - Acquisition DAQ")
        self.setGeometry(100, 100, 800, 600)

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Liste des canaux
        self.channel_list = QListWidget()
        self.channel_list.setMinimumWidth(250)
        main_layout.addWidget(self.channel_list)
        
        # Zone de visualisation (à compléter)
        self.plot_widget = QWidget()
        self.plot_widget.setStyleSheet("background: #f0f0f0;")
        main_layout.addWidget(self.plot_widget)