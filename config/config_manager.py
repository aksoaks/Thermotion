import json
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path='config/default_config.json'):
        self.config_path = Path(config_path)
        self._ensure_config_exists()
        self.config = self._load_config()

    def _ensure_config_exists(self):
        """Crée le fichier config s'il n'existe pas"""
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "version": 1,
                "modules": []
            }
            self.save_config(default_config)

    def _load_config(self):
        """Charge la configuration depuis le fichier"""
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self, config):
        """Sauvegarde la configuration"""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
        self.config = config