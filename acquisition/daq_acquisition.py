import nidaqmx
from nidaqmx.constants import ThermocoupleType, TemperatureUnits
from nidaqmx.stream_readers import AnalogMultiChannelReader
import numpy as np

# Convertisseur texte -> DAQmx
THERMOCOUPLE_MAP = {
    "K": ThermocoupleType.K,
    "T": ThermocoupleType.T,
    "J": ThermocoupleType.J,
    "E": ThermocoupleType.E,
    "N": ThermocoupleType.N,
    "R": ThermocoupleType.R,
    "S": ThermocoupleType.S,
    "B": ThermocoupleType.B,
}

def read_all_temperatures(config, sample_rate=1.0):
    """Lit la température sur tous les canaux actifs et configurés."""
    active_channels = []

    for device_name, device_cfg in config.get("devices", {}).items():
        if not device_cfg.get("enabled", True):
            continue

        for channel_id, ch_cfg in device_cfg.get("channels", {}).items():
            if not ch_cfg.get("enabled", True):
                continue

            thermo_type = ch_cfg.get("thermocouple_type", "K")
            tc_enum = THERMOCOUPLE_MAP.get(thermo_type, ThermocoupleType.K)

            active_channels.append((channel_id, tc_enum))

    if not active_channels:
        raise RuntimeError("Aucun canal actif configuré.")

    with nidaqmx.Task() as task:
        for ch_id, tc_type in active_channels:
            task.ai_channels.add_ai_thrmcpl_chan(
                physical_channel=ch_id,
                thermocouple_type=tc_type,
                units=TemperatureUnits.DEG_C
            )

        task.timing.cfg_samp_clk_timing(rate=sample_rate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=1)

        reader = AnalogMultiChannelReader(task.in_stream)
        data = np.zeros((len(active_channels), 1), dtype=np.float64)
        reader.read_many_sample(data, number_of_samples_per_channel=1)

    return {ch_id: float(val[0]) for (ch_id, _), val in zip(active_channels, data)}
