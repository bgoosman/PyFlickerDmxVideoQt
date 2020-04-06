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

app = QApplication([])
appState = AppState(app)
DEFAULT_BPM = 20
centralWidget = QWidget()
imageView = QLabel(centralWidget) if not simulate else MagicClass('QLabel')
cv2 = cv2 if not simulate else MagicClass('cv2')
actionFactory = ActionFactory(simulate)
timerFactory = TimerFactory(simulate)
frameTimer = MagicClass('FrameTimer') if simulate else None
videoCapture = cv2.VideoCapture(0)
videoStream = VideoStream(videoCapture) if not simulate else MagicClass('VideoStream')
link = LinkToPy.LinkInterface('/Applications/Carabiner') if not simulate else MockLink()
set = live.Set() if not simulate else MockSet()
ableton = Ableton(link, set, simulate)
ableton.setBpm(DEFAULT_BPM)
ableton.start()
timeline = Timeline(ableton) if not simulate else MockTimeline(ableton)
lightboard = None
try:
    lightboard = DmxLightboard('/dev/cu.usbserial-6A3MRKF6')
except Exception as e:
    lightboard = Lightboard()
    print(str(e))
lightboard.addFixture('spot1', ChauvetOvationE910FC(dmx=lightboard, startChannel=4) if not simulate else MagicClass('spot1'))
lightboard.addFixture('spot2', ChauvetOvationE910FC(dmx=lightboard, startChannel=61) if not simulate else MagicClass('spot2'))
lightboard.addFixture('par38', [Par38(lightboard, channel) if not simulate else MagicClass('Par38.%d' % channel) for channel in [221, 226, 11, 16, 31, 96, 91, 86, 46, 71]])
lightboard.addFixture('par64', [Par64(lightboard, channel) if not simulate else MagicClass('Par64.%d' % channel) for channel in [121, 126, 131, 136, 116, 111, 101, 139, 142]])
videoArchive = VideoArchive() if not simulate else MagicClass('VideoArchive')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0002-empty.mp4')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0003-se1.mov')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0004-se2.mp4')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0005-sandals.mp4')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0006-tracksuit.mp4')
videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0007-underwear.mp4')
appWindow = AppWindow(
    appState=appState,
    centralWidget=centralWidget,
    imageView=imageView,
    cv2=cv2,
    actionFactory=actionFactory,
    timerFactory=timerFactory,
    frameTimer=frameTimer,
    videoStream=videoStream,
    ableton=ableton,
    timeline=timeline,
    lightboard=lightboard,
    videoArchive=videoArchive,
    simulate=simulate
)
appWindow.showFullScreen()
appWindow.startPerformance()
if simulate:
    while not timeline.isEmpty():
        timeline.cueNextAction()
    exit(0)
app.exit(app.exec_())
