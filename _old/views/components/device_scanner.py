from PySide6.QtWidgets import QDialog, QVBoxLayout, QGroupBox
from PySide6.QtCore import Signal
import nidaqmx
from ..models.device_model import DeviceModel

class DeviceScanner(QDialog):
    devices_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_model = DeviceModel()
        self.init_ui()

    def scan_devices(self):
        """Même implémentation que dans l'ancien script"""
        devices = self.device_model.detect_devices()
        self.devices_updated.emit(devices)