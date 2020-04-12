from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pyCreative import *

frame_width = 1280
frame_height = 720
MILLISECONDS_IN_SECOND = 1000.0
UPDATES_PER_SECOND = 300.0

class AppWindow(QMainWindow):
    def __init__(self):
        QWidget.__init__(self, None)
        self.centralWidget = QWidget()
        self.imageView = QLabel(self.centralWidget)
        self.setCentralWidget(self.centralWidget)
        self.setBackgroundColor(Qt.black)
        self.imageView = self.imageView
        self.appTimer = None
        self.uiThreadFunctions = []

    def update(self):
        Event('appTimerUpdate')
        for f in self.uiThreadFunctions:
            f()
        self.uiThreadFunctions = []

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Q:
            Event('quit')
        elif key == Qt.Key_Semicolon:
            Event('scanAbletonSet')
        elif key == Qt.Key_Apostrophe:
            Event('saveAbletonSet')
        elif key == Qt.Key_O:
            Event('stopPerformance')
        elif key == Qt.Key_P:
            Event('startPerformance')

    def closeEvent(self, event):
        Event('quit')

    def resizeEvent(self, event):
        scaled_width = self.width()
        ratio = scaled_width / frame_width
        scaled_height = frame_height * ratio
        self.imageView.setFixedSize(QSize(scaled_width, scaled_height))

    def setBackgroundColor(self, color):
        palette = self.palette()
        palette.setColor(self.backgroundRole(), color)
        self.setPalette(palette)

    def displayFrame(self, frame):
        if frame is None:
            self.imageView.clear()
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 1)
        scaled_width = int(self.width())
        ratio = scaled_width / frame_width
        scaled_height = int(frame_height * ratio)
        frame = cv2.resize(frame, (scaled_width, scaled_height))
        qImage = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        self.imageView.setPixmap(QPixmap.fromImage(qImage))

    def clearFrame(self):
        self.imageView.clear()

    def startAppTimer(self):
        self.appTimer = QTimer()
        self.appTimer.timeout.connect(self.update)
        timeout = MILLISECONDS_IN_SECOND / UPDATES_PER_SECOND
        self.appTimer.start(timeout)

    def stopAppTimer(self):
        if self.appTimer is not None:
            self.appTimer.stop()

    def executeOnUiThread(self, f):
        self.uiThreadFunctions.append(f)

    def quit(self):
        if self.appTimer is not None:
            self.appTimer.stop()

