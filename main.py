from PyQt5.QtWidgets import *
from AppState import AppState
from AppWindow import AppWindow
import sys

simulate = False
if "-simulate" in sys.argv:
    simulate = True

app = QApplication([])
appState = AppState(app)
win = AppWindow(appState, simulate=simulate)
win.showFullScreen()
app.exit(app.exec_())
