import random
import sys

import cv2
import live
import LinkToPy
from PyQt5.QtWidgets import *
from pyCreative.Lightboard import *
from pyCreative.MagicClass import *
from pyCreative.Timeline import *
from pyCreative.VideoStream import *

from ActionFactory import *
from AppState import *
from AppWindow import *
from TimerFactory import *
from VideoArchive import *

simulate = False
if "--simulate" in sys.argv:
    simulate = True

random.seed(10)

class SoftwareEngineerPerformance(Observer):
    DEFAULT_BPM = 20

    def __init__(self):
        Observer.__init__(self)
        self.app = QApplication([])
        self.appState = AppState(self.app)
        self.actionFactory = ActionFactory(simulate)
        self.timerFactory = TimerFactory(simulate)
        self.frameTimer = MagicClass('FrameTimer') if simulate else None
        self.videoCapture = cv2.VideoCapture(0)
        self.frame = cv2.imread('cat.jpg')
        self.videoStream = VideoStream(self.videoCapture) if not simulate else MockVideoStream('VideoStream', self.frame)
        self.link = LinkToPy.LinkInterface('/Applications/Carabiner') if not simulate else MockLink()
        self.abletonSet = live.Set() if not simulate else MockSet()
        self.ableton = Ableton(self.link, self.abletonSet, simulate)
        self.ableton.setBpm(SoftwareEngineerPerformance.DEFAULT_BPM)
        self.ableton.start()
        self.timeline = Timeline(self.ableton) if not simulate else MockTimeline(self.ableton)
        try:
            self.lightboard = DmxLightboard('/dev/cu.usbserial-6A3MRKF6')
        except Exception as e:
            self.lightboard = Lightboard()
            print(str(e))
        self.lightboard.addFixture('spot1', ChauvetOvationE910FC(dmx=self.lightboard, startChannel=4) if not simulate else MagicClass('spot1'))
        self.lightboard.addFixture('spot2', ChauvetOvationE910FC(dmx=self.lightboard, startChannel=61) if not simulate else MagicClass('spot2'))
        self.lightboard.addFixture('par38', [Par38(self.lightboard, channel) if not simulate else MagicClass('Par38.%d' % channel) for channel in [221, 226, 11, 16, 31, 96, 91, 86, 46, 71]])
        self.lightboard.addFixture('par64', [Par64(self.lightboard, channel) if not simulate else MagicClass('Par64.%d' % channel) for channel in [121, 126, 131, 136, 116, 111, 101, 139, 142]])
        self.videoArchive = VideoArchive() if not simulate else MockVideoArchive('VideoArchive', self.frame)
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0002-empty.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0003-se1.mov')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0004-se2.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0005-sandals.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0006-tracksuit.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0007-underwear.mp4')
        centralWidget = QWidget()
        imageView = QLabel(centralWidget)
        self.appWindow = AppWindow(
            appState=self.appState,
            centralWidget=centralWidget,
            imageView=imageView,
            cv2=cv2,
            actionFactory=self.actionFactory,
            timerFactory=self.timerFactory,
            frameTimer=self.frameTimer,
            videoStream=self.videoStream,
            ableton=self.ableton,
            timeline=self.timeline,
            lightboard=self.lightboard,
            videoArchive=self.videoArchive,
            simulate=simulate
        )
        self.observe('appWindowUpdate', self.update)
        self.observe('startPerformance', self.startPerformance)
        self.observe('stopPerformance', self.stopPerformance)
        self.observe('scanAbletonSet', self.scanAbletonSet)
        self.observe('saveAbletonSet', self.saveAbletonSet)
        self.observe('quit', self.quit)
        self.appWindow.showFullScreen()

        if simulate:
            self.appWindow.frame = self.frame
            self.appWindow.startPerformance()
            while not self.timeline.isEmpty():
                self.appWindow.update()
            exit(0)

        self.app.exit(self.app.exec_())

    def update(self):
        self.timeline.update()
        self.lightboard.update()

    def startPerformance(self):
        self.appWindow.startPerformance()

    def stopPerformance(self):
        self.appWindow.stopPerformance()

    def scanAbletonSet(self):
        self.ableton.scan()

    def saveAbletonSet(self):
        self.ableton.set.save()

    def quit(self):
        self.appWindow.quit()

performance = SoftwareEngineerPerformance()
