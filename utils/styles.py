import nidaqmx.system

class DAQManager:
    def __init__(self):
        self.system = nidaqmx.system.System.local()
    
    def get_devices(self):
        """Retourne la liste des appareils NI-DAQ disponibles"""
        return self.system.devices