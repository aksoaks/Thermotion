import nidaqmx.system

system = nidaqmx.system.System.local()

print("Appareils NI-DAQmx détectés :")
for device in system.devices:
    print(f"- {device.name} (Type: {device.product_type})")
    print(f"  Modules/Channels: {[chan.name for chan in device.ai_physical_chans]}")