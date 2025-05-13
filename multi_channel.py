# multi_channel.py

import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from utils.nidaq_utils import setup_multichannel_task
from utils.plotting import setup_plot, update_plot
from nidaqmx.system import System

def find_first_ai_channels(n_channels=2):
    """Trouve les n premiers canaux analogiques disponibles."""
    for device in System.local().devices:
        chans = list(device.ai_physical_chans)
        if len(chans) >= n_channels:
            return [chan.name for chan in chans[:n_channels]]
    return []

class MultiChannelApp(QtWidgets.QMainWindow):
    def __init__(self, channels, rate=1000.0, samples_per_channel=100):
        super().__init__()
        self.channels = channels
        self.rate = rate
        self.samples_per_channel = samples_per_channel

        # Créer la tâche et le lecteur de données
        self.task, self.reader, self.buffer = setup_multichannel_task(
            self.channels, self.rate, self.samples_per_channel
        )

        # Interface graphique
        self.win, self.plots, self.curves = setup_plot(len(self.channels))
        self.setCentralWidget(self.win)
        self.setWindowTitle("Acquisition multicanal NI-DAQmx")

        # Timer pour lecture continue
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_data)
        interval_ms = int(1000 * self.samples_per_channel / self.rate)
        self.timer.start(interval_ms)

        self.task.start()

    def update_data(self):
        try:
            self.reader.read_many_sample(
                self.buffer,
                number_of_samples_per_channel=self.samples_per_channel
            )
            update_plot(self.curves, self.buffer)
        except Exception as e:
            print(f"[ERREUR] Problème d'acquisition : {e}")

    def closeEvent(self, event):
        self.timer.stop()
        self.task.stop()
        self.task.close()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Détection des canaux disponibles
    channels = find_first_ai_channels(n_channels=2)
    if not channels:
        print("[ERREUR] Aucun canal analogique détecté.")
        sys.exit(1)
    
    print(f"[INFO] Acquisition sur les canaux : {channels}")

    main_window = MultiChannelApp(channels)
    main_window.show()
    sys.exit(app.exec_())
