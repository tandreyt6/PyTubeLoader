import logging
import os
import sys
import traceback
from datetime import datetime

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QIcon

from ui.MainWindow import MainWindow
from func import resources

if __name__ == '__main__':
    class ErrorOnlyFileHandler(logging.FileHandler):
        def __init__(self, filename, mode='a', encoding=None, delay=False):
            self.has_errors = False
            super().__init__(filename, mode, encoding, delay)

        def emit(self, record):
            if record.levelno >= logging.ERROR:
                self.has_errors = True
                super().emit(record)

        def close(self):
            if not self.has_errors:
                super().close()
                if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) == 0:
                    os.remove(self.baseFilename)
            else:
                super().close()


    def get_log_filename(base_name="ytd_error"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("./logs/", exist_ok=True)
        log_file = f"./logs/{base_name}.log"

        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            log_file = f"./logs/{base_name}_{timestamp}.log"

        return log_file


    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    handler = ErrorOnlyFileHandler(get_log_filename())
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


    def log_exception(exc_type, exc_value, exc_traceback):
        print(exc_type, exc_value, exc_traceback)
        logger.error(
            "Exception Error:\n%s",
            ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )


    sys.excepthook = log_exception

    app = QApplication([])
    icon = QPixmap()
    icon.loadFromData(bytes(resources.bin), format='ico')
    app.setWindowIcon(QIcon(icon))

    win = MainWindow()
    win.showNormal()

    app.exec()