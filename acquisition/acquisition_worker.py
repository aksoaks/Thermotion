from PySide6.QtCore import QObject, Signal, QTimer
import nidaqmx
from nidaqmx.constants import TemperatureUnits, ThermocoupleType
import time

type_map = {
    "K": ThermocoupleType.K,
    "J": ThermocoupleType.J,
    "T": ThermocoupleType.T,
    "E": ThermocoupleType.E,
    "R": ThermocoupleType.R,
    "S": ThermocoupleType.S,
    "B": ThermocoupleType.B,
    "N": ThermocoupleType.N
}

class AcquisitionWorker(QObject):
    new_data = Signal(dict)
    finished = Signal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        self.timer = None  # Déclaré mais pas encore instancié

    def start(self):
        self.running = True
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.acquire_once)
        self.timer.start()

    def stop(self):
        self.running = False
        self.timer.stop()
        self.finished.emit()

    def acquire_once(self):
        if not self.running:
            return

        readings = {}
        for device_name, dev_cfg in self.config.get("devices", {}).items():
            if not dev_cfg.get("enabled"):
                continue

            for ch_id, ch_cfg in dev_cfg.get("channels", {}).items():
                if not ch_cfg.get("enabled", True):
                    continue
                try:
                    with nidaqmx.Task() as task:
                        thermocouple_type = type_map.get(
                            ch_cfg.get("thermocouple_type", "K"),
                            ThermocoupleType.K
                        )
                        task.ai_channels.add_ai_thrmcpl_chan(
                            ch_id,
                            thermocouple_type=thermocouple_type,
                            units=TemperatureUnits.DEG_C,
                            cjc_source=nidaqmx.constants.CJCSource.BUILT_IN
                        )
                        value = task.read()
                        readings[ch_id] = value
                except Exception as e:
                    print(f"[Worker] Error on {ch_id}: {e}")
                    readings[ch_id] = None

        self.new_data.emit(readings)
