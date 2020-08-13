import logging
import sys
import threading
import traceback
import warnings

from PySide2.QtCore import Qt
from PySide2.QtGui import QPalette, QColor
from PySide2.QtWidgets import QApplication, QMessageBox
from matplotlib import font_manager

import __info__
from fileio.extrap3_experiment_reader import read_extrap3_experiment
from fileio.json_file_reader import read_json_file
from fileio.text_file_reader import read_text_file
from gui.MainWidget import MainWidget
from util.exceptions import RecoverableError


def _preload_common_fonts():
    common_fonts = [
        font_manager.FontProperties('sans\\-serif:style=normal:variant=normal:weight=normal:stretch=normal:size=10.0'),
        'STIXGeneral', 'STIXGeneral:italic', 'STIXGeneral:weight=bold',
        'STIXNonUnicode', 'STIXNonUnicode:italic', 'STIXNonUnicode:weight=bold',
        'STIXSizeOneSym', 'STIXSizeTwoSym', 'STIXSizeThreeSym', 'STIXSizeFourSym', 'STIXSizeFiveSym',
        'cmsy10', 'cmr10', 'cmtt10', 'cmmi10', 'cmb10', 'cmss10', 'cmex10',
        'DejaVu Sans', 'DejaVu Sans:italic', 'DejaVu Sans:weight=bold', 'DejaVu Sans Mono', 'DejaVu Sans Display',
        font_manager.FontProperties('sans\\-serif:style=normal:variant=normal:weight=normal:stretch=normal:size=12.0'),
        font_manager.FontProperties('sans\\-serif:style=normal:variant=normal:weight=normal:stretch=normal:size=6.0')
    ]

    def _thread(fonts):
        for f in fonts:
            font_manager.findfont(f)

    thread = threading.Thread(target=_thread, args=(common_fonts,))
    thread.start()
    return thread


def main(*, test=False):
    # preload fonts for matplotlib
    font_preloader = _preload_common_fonts()

    # TODO: add logging to the gui application
    if '--debug' in sys.argv:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
    else:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    app = QApplication(sys.argv) if not test else QApplication.instance()
    app.setStyle('Fusion')
    # app.setStyleSheet('QWidget{background:#333;color:#eee}')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(190, 190, 190))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, QColor(220, 220, 220))
    palette.setColor(QPalette.AlternateBase, QColor(10, 10, 10))
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(220, 220, 220))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.Highlight, QColor(31, 119, 180))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(80, 80, 80))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(80, 80, 80))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(150, 150, 150))
    app.setPalette(palette)

    window = MainWidget()

    _old_warnings_handler = warnings.showwarning
    _old_exception_handler = sys.excepthook

    def _warnings_handler(message: Warning, category, filename, lineno, file=None, line=None):
        msgBox = QMessageBox(window)
        msgBox.setWindowTitle('Warning')
        msgBox.setIcon(QMessageBox.Icon.Warning)
        msgBox.setText(str(message))
        if not test:
            msgBox.open()
        return _old_warnings_handler(message, category, filename, lineno, file, line)

    def _exception_handler(type, value, traceback_):
        msgBox = QMessageBox(window)
        if hasattr(value, 'NAME'):
            msgBox.setWindowTitle(__info__.__title__)
        else:
            msgBox.setWindowTitle('Error')
        msgBox.setIcon(QMessageBox.Icon.Critical)
        msgBox.setText(str(value))
        traceback_lines = traceback.extract_tb(traceback_).format()
        msgBox.setDetailedText(''.join(traceback_lines))
        if test:
            return _old_exception_handler(type, value, traceback_)
        if issubclass(type, RecoverableError):
            _old_exception_handler(type, value, traceback_)
            msgBox.open()
        else:
            _old_exception_handler(type, value, traceback_)
            msgBox.exec_()  # ensures waiting
            exit(1)

    warnings.showwarning = _warnings_handler
    sys.excepthook = _exception_handler

    window.show()

    if len(sys.argv) >= 3 and '--text' == sys.argv[1]:
        experiment = read_text_file(sys.argv[2])
        # call the modeler and create a function model
        window.model_experiment(experiment)
    elif len(sys.argv) >= 3 and '--json' == sys.argv[1]:
        experiment = read_json_file(sys.argv[2])
        # call the modeler and create a function model
        window.model_experiment(experiment)
    elif len(sys.argv) >= 3 and '--extra-p-3' == sys.argv[1]:
        experiment = read_extrap3_experiment(sys.argv[2])
        # call the modeler and create a function model
        window.setExperiment(experiment)

    if not test:
        app.exec_()
        font_preloader.join()
    else:
        font_preloader.join()
        return window, app


if __name__ == "__main__":
    main()
