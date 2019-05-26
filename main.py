from PyQt5.QtWidgets import *
from AppState import AppState
from AppWindow import AppWindow

app = QApplication([])
appState = AppState(app)
win = AppWindow(appState)
win.showFullScreen()
app.exit(app.exec_())
