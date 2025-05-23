from PySide6.QtWidgets import QMainWindow, QListWidget
from config.config_manager import ConfigManager  # Import crucial ajouté ici

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()  # Maintenant reconnu
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Thermotion DAQ")
        self.setGeometry(100, 100, 800, 600)
        
        # Liste des canaux
        self.channel_list = QListWidget(self)
        self.channel_list.setGeometry(10, 10, 200, 580)