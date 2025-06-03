import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from PySide6.QtGui import QColor, QIcon, QFont, QIcon, QPixmap

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)  # ✅ pour la barre des tâches

    if not QIcon.hasThemeIcon("document-edit"):
        QIcon.setThemeName("breeze")

    window = MainWindow()   
    window.show()
    sys.exit(app.exec())
