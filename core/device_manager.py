import nidaqmx.system

def detect_daq_modules():
    try:
        system = nidaqmx.system.System.local()
        return [d for d in system.devices if "Mod" in d.name]
    except Exception as e:
        print(f"Error detecting devices: {e}")
        return []

def get_online_devices():
    try:
        system = nidaqmx.system.System.local()
        return [d.name for d in system.devices]
    except Exception as e:
        print(f"Error listing devices: {e}")
        return []
