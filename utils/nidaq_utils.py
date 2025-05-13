# utils/nidaq_utils.py

import nidaqmx
import numpy as np
from nidaqmx.constants import ThermocoupleType, TemperatureUnits

def setup_multichannel_task(channels, rate, samples_per_channel):
    task = nidaqmx.Task()

    # Ajouter les canaux thermocouples (Type T)
    for ch in channels:
        task.ai_channels.add_ai_thrmcpl_chan(
            physical_channel=ch,
            name_to_assign_to_channel='',
            min_val=0.0,
            max_val=400.0,  # Plage typique pour thermocouples type T
            units=TemperatureUnits.DEG_C,
            thermocouple_type=ThermocoupleType.T,
            cjc_source=nidaqmx.constants.CJCSource.BUILT_IN
        )

    # Configurer le timing d'acquisition
    task.timing.cfg_samp_clk_timing(
        rate,
        sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=samples_per_channel
    )

    # Créer un buffer pour les données lues
    buffer = np.zeros((len(channels), samples_per_channel))

    # Créer le lecteur de données
    reader = nidaqmx.readers.AnalogMultiChannelReader(task.in_stream)

    return task, reader, buffer
