import sys

from PyQt5.QtWidgets import QApplication

from app import MainWindow


def start_app():
    marker = 'Battery Check'
    app = QApplication(sys.argv)
    app_window = MainWindow(marker=marker)
    app_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    start_app()


