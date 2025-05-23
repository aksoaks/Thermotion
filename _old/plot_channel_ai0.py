import threading
from queue import Queue
import nidaqmx
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QMessageBox, QComboBox, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
import numpy as np
from datetime import datetime
import csv
import os
import time

# Configuration initiale
DEFAULT_CHANNEL = "cDAQ1Mod1/ai0"
BUFFER_SIZE = 3600  # 1 heure de données
THERMOCOUPLE_TYPE = nidaqmx.constants.ThermocoupleType.T
DATA_FOLDER = "Thermocouple_Data"

class ThermocoupleMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.device = DEFAULT_CHANNEL
        self.device_connected = True
        self.channel_alias = "ai0"
        
        # Initialisation du temps de référence
        self.start_timestamp = datetime.now()  
        self.time_offset = 0  # Pour ajustements
        
        # Queue pour communication inter-threads
        self.data_queue = Queue()
        self.stop_event = threading.Event()
        
        self.setup_ui()
        self.setup_data_handling()

    def setup_ui(self):
        self.setWindowTitle("Thermocouple Monitor Pro")
        self.resize(1400, 700)

        # Layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Graphique
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.plot = self.graph_widget.addPlot(title="Temperature en temps reel")
        self.plot.setLabel('left', 'Temperature (degC)')
        self.plot.setLabel('bottom', 'Time')
        self.plot.showGrid(x=True, y=True)
        self.plot.setAxisItems({'bottom': pg.DateAxisItem()})
        self.curve = self.plot.plot(pen=pg.mkPen('r', width=2), name="Thermocouple T")
        main_layout.addWidget(self.graph_widget, stretch=4)

        # Panneau de contrôle
        control_panel = QWidget()
        control_panel.setMaximumWidth(300)
        control_layout = QVBoxLayout(control_panel)

        # Widgets de contrôle
        self.status_label = QLabel("État: Connecté")
        self.current_temp = QLabel("--.-- C")
        self.export_btn = QPushButton("Exporter données")
        self.connect_btn = QPushButton("Reconnecter")

        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.current_temp)
        control_layout.addWidget(self.export_btn)
        control_layout.addWidget(self.connect_btn)
        control_layout.addStretch()
        main_layout.addWidget(control_panel)

        # Connexions
        self.export_btn.clicked.connect(self.export_data)
        self.connect_btn.clicked.connect(self.reconnect_device)
        self.connect_btn.setEnabled(False)

    def setup_data_handling(self):
        self.timestamps = np.zeros(BUFFER_SIZE)
        self.temperatures = np.zeros(BUFFER_SIZE)
        self.ptr = 0
        os.makedirs(DATA_FOLDER, exist_ok=True)

        # Thread d'acquisition
        self.acquisition_thread = threading.Thread(
            target=self.acquisition_worker,
            daemon=True
        )
        self.acquisition_thread.start()

        # Timer pour mise à jour UI
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(100)  # Rafraîchissement UI toutes les 100ms

    def acquisition_worker(self):
        """Thread dédié à l'acquisition des données"""
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_thrmcpl_chan(
                        self.device,
                        thermocouple_type=THERMOCOUPLE_TYPE,
                        units=nidaqmx.constants.TemperatureUnits.DEG_C
                    )
                    temp = task.read()
                
                now = datetime.now()
                timestamp = now.timestamp()
                
                # Envoi des données au thread principal via Queue
                self.data_queue.put((timestamp, temp, now))
                
                # Respect du timing 1Hz
                elapsed = time.time() - start_time
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                    
            except nidaqmx.errors.DaqError as e:
                self.data_queue.put(('error', e))
                time.sleep(1.0)

    def update_ui(self):
        """Mise à jour de l'interface depuis le thread principal"""
        while not self.data_queue.empty():
            data = self.data_queue.get()
            
            if data[0] == 'error':
                self.handle_daq_error(data[1])
            else:
                timestamp, temp, now = data
                
                # Calcul du temps écoulé depuis le démarrage
                self.timestamps[self.ptr] = timestamp  # Stocker le timestamp brut UNIX
                self.temperatures[self.ptr] = temp
                self.ptr = (self.ptr + 1) % BUFFER_SIZE

                # Mise à jour graphique
                valid_data = self.timestamps != 0
                self.curve.setData(self.timestamps[valid_data], self.temperatures[valid_data])
                self.current_temp.setText(f"{temp:.2f}".replace('.', ',') + " C")
                
                if np.any(valid_data):
                    self.plot.setXRange(np.min(self.timestamps[valid_data]), np.max(self.timestamps[valid_data]))


                # Sauvegarde avec heure absolue
                self.save_to_csv(now, temp)
                
                self.device_connected = True
                self.status_label.setText("État: Connecté")

    def handle_daq_error(self, error):
        if error.error_code == -201003:  # Appareil non détecté
            if self.device_connected:
                QMessageBox.critical(self, "Erreur", "Appareil non détecté!")
            self.device_connected = False
            self.status_label.setText("État: Déconnecté")
            self.connect_btn.setEnabled(True)

    def save_to_csv(self, timestamp, temperature):
        today_file = os.path.join(DATA_FOLDER, f"data_{timestamp.strftime('%Y%m%d')}.csv")
        header = not os.path.exists(today_file)

        with open(today_file, 'a', newline='', encoding='ascii') as f:
            writer = csv.writer(f, delimiter=';')
            if header:
                writer.writerow(["Date/Heure", "Temperature (C)"])
            writer.writerow([
                timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                str(temperature).replace('.', ',')
            ])

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter les données",
            datetime.now().strftime("Export_%Y-%m-%d_%H-%M-%S.csv"),
            "CSV Files (*.csv)"
        )

        if file_path:
            with open(file_path, 'w', newline='', encoding='ascii') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Date/Heure", "Temperature (C)"])
                for ts, temp in zip(self.timestamps, self.temperatures):
                    if ts > 0:
                        dt = datetime.fromtimestamp(ts)
                        writer.writerow([
                            dt.strftime("%d/%m/%Y %H:%M:%S"),
                            f"{temp:.2f}".replace('.', ',')
                        ])

    def reconnect_device(self):
        self.status_label.setText("État: Reconnexion...")
        QApplication.processEvents()
        if not self.acquisition_thread.is_alive():
            self.stop_event.clear()
            self.acquisition_thread = threading.Thread(
                target=self.acquisition_worker,
                daemon=True
            )
            self.acquisition_thread.start()

    def closeEvent(self, event):
        """Nettoyage à la fermeture"""
        self.stop_event.set()
        self.acquisition_thread.join()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication([])
    window = ThermocoupleMonitor()
    window.show()
    app.exec()

    '''class ThermocoupleMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        # [...] (initialisations existantes)
        
        # Nouveaux attributs pour la gestion des devices
        self.available_devices = []
        self.available_channels = []
        self.channel_widgets = {}  # Pour stocker les éléments UI par voie
        
        # [...] (suite de l'initialisation)

    def setup_ui(self):
        # [...] (contenu existant)
        
        # Ajout du bouton de détection
        self.detect_btn = QPushButton("Check new devices")
        self.detect_btn.clicked.connect(self.detect_devices)
        control_layout.insertWidget(0, self.detect_btn)  # Ajout en haut du panneau

        # Zone pour l'affichage des voies
        self.channels_group = QGroupBox("Voies Thermocouples")
        self.channels_layout = QVBoxLayout()
        self.channels_group.setLayout(self.channels_layout)
        control_layout.insertWidget(1, self.channels_group)

    def detect_devices(self):
        """Détection des appareils et voies disponibles"""
        try:
            system = nidaqmx.system.System.local()
            self.available_devices = [d.name for d in system.devices if "Mod" in d.name]
            
            # Détection des voies thermocouples
            self.available_channels = []
            for device in self.available_devices:
                for i in range(8):  # On suppose 8 voies max par module
                    channel = f"{device}/ai{i}"
                    try:
                        with nidaqmx.Task() as test_task:
                            test_task.ai_channels.add_ai_thrmcpl_chan(channel)
                            self.available_channels.append(channel)
                    except:
                        continue
            
            self.update_channels_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Detection failed: {str(e)}")

    def update_channels_ui(self):
        """Mise à jour de l'interface pour les voies détectées"""
        # Nettoyage de l'UI existante
        for i in reversed(range(self.channels_layout.count())): 
            self.channels_layout.itemAt(i).widget().setParent(None)
        self.channel_widgets.clear()
        
        # Création des éléments UI pour chaque voie
        for i, channel in enumerate(self.available_channels):
            channel_frame = QWidget()
            channel_layout = QHBoxLayout(channel_frame)
            
            # Checkbox pour activation
            chk = QCheckBox(f"Voie {i+1}")
            chk.setChecked(i == 0)  # Active la première voie par défaut
            
            # Label pour valeur
            lbl = QLabel("--.-- °C")
            lbl.setAlignment(Qt.AlignRight)
            
            channel_layout.addWidget(chk)
            channel_layout.addWidget(lbl)
            self.channels_layout.addWidget(channel_frame)
            
            # Stockage des références
            self.channel_widgets[channel] = {
                'checkbox': chk,
                'label': lbl,
                'active': (i == 0)
            }
            
            # Connexion du checkbox
            chk.stateChanged.connect(
                lambda state, c=channel: self.toggle_channel(c, state)
            )
        
        if not self.available_channels:
            self.channels_layout.addWidget(QLabel("Aucune voie détectée"))

    def toggle_channel(self, channel, state):
        """Active/désactive une voie spécifique"""
        self.channel_widgets[channel]['active'] = (state == Qt.Checked)
        
    def acquisition_worker(self):
        """Thread d'acquisition modifié pour plusieurs voies"""
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                readings = {}
                
                # Acquisition pour toutes les voies actives
                for channel, widgets in self.channel_widgets.items():
                    if widgets['active']:
                        with nidaqmx.Task() as task:
                            task.ai_channels.add_ai_thrmcpl_chan(
                                channel,
                                thermocouple_type=THERMOCOUPLE_TYPE,
                                units=nidaqmx.constants.TemperatureUnits.DEG_C
                            )
                            temp = task.read()
                            readings[channel] = temp
                
                now = datetime.now()
                self.data_queue.put((now.timestamp(), readings, now))
                
                # Respect du timing 1Hz
                elapsed = time.time() - start_time
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                    
            except nidaqmx.errors.DaqError as e:
                self.data_queue.put(('error', e))
                time.sleep(1.0)

    def update_ui(self):
        """Mise à jour de l'interface pour plusieurs voies"""
        while not self.data_queue.empty():
            data = self.data_queue.get()
            
            if data[0] == 'error':
                self.handle_daq_error(data[1])
            else:
                timestamp, readings, now = data
                
                # Mise à jour de toutes les voies
                for channel, temp in readings.items():
                    if channel in self.channel_widgets:
                        lbl = self.channel_widgets[channel]['label']
                        lbl.setText(f"{temp:.2f} °C")
                
                # [...] (le reste de la mise à jour comme avant)'''