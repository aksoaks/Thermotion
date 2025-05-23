import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path='config/default_config.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        """Charge la configuration depuis le fichier"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self, config):
        """Sauvegarde la configuration"""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
        self.config = config