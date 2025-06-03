from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer

class LoadingDialog(QDialog):
    def __init__(self, message="Chargement..."):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setStyleSheet("background-color: #222; color: white; font-size: 14px;")
        self.setFixedSize(300, 100)

        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self._value = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(30)  # ~30ms * 100 = 3s (approx.)

        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                background: #333;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                width: 20px;
            }
        """)
        layout.addWidget(self.progress)

    def _update_progress(self):
        if self._value >= 100:
            self.timer.stop()
        else:
            self._value += 1
            self.progress.setValue(self._value)
