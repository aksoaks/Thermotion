import nidaqmx
from nidaqmx.errors import DaqError
from typing import List, Dict

class DeviceModel:
    def detect_devices(self) -> List[Dict]:
        try:
            system = nidaqmx.system.System.local()
            return [
                {
                    "name": dev.name,
                    "channels": [ch.name for ch in dev.ai_physical_chans]
                } 
                for dev in system.devices 
                if "Mod" in dev.name
            ]
        except DaqError as e:
            raise Exception(f"NI-DAQmx Error: {str(e)}")