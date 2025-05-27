import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from PySide6.QtGui import QColor, QIcon, QFont, QIcon, QPixmap

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if not QIcon.hasThemeIcon("document-edit"):
        QIcon.setThemeName("breeze")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
