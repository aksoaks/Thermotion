from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
import pyqtgraph as pg
from config.config_manager import ConfigManager
from views.components.device_scanner import DeviceScanner
from views.components.channel_config_dialog import ChannelConfigDialog

class MainWindow(QMainWindow):
    data_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """Reproduit exactement l'UI de l'ancien script"""
        self.setWindowTitle("Thermotion DAQ")
        self.resize(1200, 800)

        # Layout principal identique à l'ancienne version
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Partie gauche - Arborescence
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Partie centrale - Graphique
        self.plot_widget = pg.PlotWidget()
        self._setup_plot_widget()
        main_layout.addWidget(self.plot_widget, 3)

        # Partie droite - Configuration
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 1)

    def _setup_plot_widget(self):
        """Configuration identique à l'ancien script"""
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Voltage', 'V')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        self.plot_widget.addLegend()

    # ... autres méthodes à copier de l'ancien script ...