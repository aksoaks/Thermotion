import sys
from PyQt5.QtWidgets import QApplication
from nidaqmx import system
from utils.nidaq_utils import detect_devices
from utils.plotting import DAQMonitor
from utils.nidaq_utils import list_devices, setup_multichannel_task
from utils.plotting import setup_plot, update_plot


def main():
    app = QApplication(sys.argv)
    
    # Détection initiale des appareils
    devices = system.System.local().devices
    channels = []
    for device in devices:
        channels.extend([chan.name for chan in device.ai_physical_chans])
    
    # Lancement de l'interface
    window = DAQMonitor(devices=devices, channels=channels)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()