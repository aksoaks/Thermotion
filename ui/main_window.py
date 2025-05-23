from PySide6.QtWidgets import QMainWindow, QListWidget
from PySide6.QtCore import Signal
from config.config_manager import ConfigManager

class MainWindow(QMainWindow):
    config_updated = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.init_ui()
        self.load_initial_config()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        # Widgets principaux
        self.channel_list = QListWidget()
        self.active_channels_list = QListWidget()
        
        # ... (setup du layout et autres widgets)
    
    def load_initial_config(self):
        """Charge la configuration initiale"""
        self.update_display(self.config_manager.config)
    
    def update_display(self, config):
        """Met à jour l'affichage avec la configuration"""
        self.channel_list.clear()
        
        for module in config.get('modules', []):
            for channel in module.get('channels', []):
                item = QListWidgetItem(f"{module['name']}/{channel['name']}")
                self.channel_list.addItem(item)