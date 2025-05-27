import json
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_path: str = "config/default_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_or_create_config()

    def _load_or_create_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {
                "version": 2,
                "devices": {},
                "active_channels": []
            }
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)