import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
from ui.main_window import MainWindow
from ui.loading_dialog import LoadingDialog

# 👇 Déclare window en global pour éviter qu’il soit détruit
window = None

def launch_main_window(loading):
    global window
    window = MainWindow()
    loading.close()
    window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Icône
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Affiche le chargement
    loading = LoadingDialog("Initialisation...")
    loading.show()

    # Lance MainWindow après 3 secondes (ou moins si tu veux)
    QTimer.singleShot(3000, lambda: launch_main_window(loading))

    sys.exit(app.exec())
