# utils/nidaq_utils.py

import nidaqmx
from nidaqmx.constants import AcquisitionType
from nidaqmx.stream_readers import AnalogMultiChannelReader
import numpy as np

def list_devices():
    """Liste les périphériques DAQ disponibles."""
    system = nidaqmx.system.System.local()
    return [device.name for device in system.devices]

def setup_multichannel_task(channels, rate=1000.0, samples_per_channel=100):
    """
    Crée et configure une tâche DAQ pour plusieurs canaux analogiques.

    Args:
        channels (list): Liste des canaux ex: ["Dev1/ai0", "Dev1/ai1"]
        rate (float): Fréquence d'échantillonnage (Hz)
        samples_per_channel (int): Nombre d'échantillons par canal

    Returns:
        task: tâche DAQmx configurée
        reader: lecteur de données multicanaux
        buffer: tampon de données numpy
    """
    task = nidaqmx.Task()
    task.ai_channels.add_ai_voltage_chan(','.join(channels))
    task.timing.cfg_samp_clk_timing(rate,
                                    sample_mode=AcquisitionType.CONTINUOUS,
                                    samps_per_chan=samples_per_channel)
    
    buffer = np.zeros((len(channels), samples_per_channel), dtype=np.float64)
    reader = AnalogMultiChannelReader(task.in_stream)

    return task, reader, buffer
