from nidaqmx.constants import ThermocoupleType

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

tc_type = config["channels"][channel_id].get("thermocouple_type", "K")
with nidaqmx.Task() as task:
    chan = task.ai_channels.add_ai_thrmcpl_chan(
        channel_id,
        thermocouple_type=type_map.get(tc_type, ThermocoupleType.K),
        units=nidaqmx.constants.TemperatureUnits.DEG_C
    )
    value = task.read()