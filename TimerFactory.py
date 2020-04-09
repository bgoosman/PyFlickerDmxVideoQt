from PyQt5.QtCore import QTimer

class TimerFactory:
    def __init__(self, simulate):
        self.simulate = simulate
        self.frameTimer = None

    def makeLocalFrameTimer(self, milliseconds, onTimeout):
        if self.simulate:
            onTimeout()
            return
        localFrameTimer = QTimer()
        localFrameTimer.timeout.connect(onTimeout)
        localFrameTimer.start(int(milliseconds))
        return localFrameTimer

    def makeGlobalFrameTimer(self, milliseconds, onTimeout):
        if self.simulate:
            onTimeout()
            return
        if self.frameTimer is not None:
            self.frameTimer.stop()
        self.frameTimer = QTimer()
        self.frameTimer.timeout.connect(onTimeout)
        self.frameTimer.start(int(milliseconds))

    def restart(self, milliseconds):
        print('Restarting frameTimer to %d milliseconds' % milliseconds)
        if self.frameTimer:
            self.frameTimer.start(milliseconds)

    def stop(self):
        if self.frameTimer:
            self.frameTimer.stop()
