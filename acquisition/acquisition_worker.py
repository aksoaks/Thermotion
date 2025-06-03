from PySide6.QtCore import QObject, Signal, QThread
import time
from nidaqmx.constants import ThermocoupleType, TemperatureUnits, CJCSource
import nidaqmx
import random

type_map = {
    "K": ThermocoupleType.K,
    "T": ThermocoupleType.T,
    "J": ThermocoupleType.J,
    "E": ThermocoupleType.E,
    "N": ThermocoupleType.N,
    "R": ThermocoupleType.R,
    "S": ThermocoupleType.S,
    "B": ThermocoupleType.B,
}

def read_all_temperatures(config):
    """Lecture instantanée des températures"""
    readings = {}

    for device_name, device_cfg in config.get("devices", {}).items():
        if not device_cfg.get("enabled", True):
            continue

        for channel_id, channel_cfg in device_cfg["channels"].items():
            if not channel_cfg.get("enabled", True):
                continue

            thermocouple_type = type_map.get(channel_cfg.get("thermocouple_type", "K"), ThermocoupleType.K)
            try:
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_thrmcpl_chan(
                        physical_channel=channel_id,
                        min_val=-200.0,
                        max_val=1350.0,
                        units=TemperatureUnits.DEG_C,
                        thermocouple_type=thermocouple_type,
                        cjc_source=CJCSource.BUILT_IN
                    )
                    value = task.read()
                    readings[channel_id] = value
            except Exception as e:
                readings[channel_id] = round(20 + random.random() * 5, 2)

    return readings

class AcquisitionWorker(QObject):
    new_data = Signal(dict)
    finished = Signal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False

    def start(self):
        self.running = True
        self.run()

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            readings = {}
            for device_name, dev_cfg in self.config.get("devices", {}).items():
                if not dev_cfg.get("enabled"):
                    continue

                for ch_id, ch_cfg in dev_cfg.get("channels", {}).items():
                    if not ch_cfg.get("enabled", True):
                        continue
                    try:
                        with nidaqmx.Task() as task:
                            thermocouple_type = type_map.get(ch_cfg.get("thermocouple_type", "K"), ThermocoupleType.K)
                            task.ai_channels.add_ai_thrmcpl_chan(
                                ch_id,
                                thermocouple_type=thermocouple_type,
                                units=TemperatureUnits.DEG_C,
                                cjc_source=nidaqmx.constants.CJCSource.BUILT_IN
                            )
                            value = task.read()
                            readings[ch_id] = value
                    except Exception as e:
                        readings[ch_id] = None  # could log the error

            self.new_data.emit(readings)
            time.sleep(1)  # polling rate

