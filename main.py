import sys
from PySide6.QtWidgets import QApplication
from app.gui import FlowConvertWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = FlowConvertWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
