import math
import random

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

from enum import Enum
class CameraState(Enum):
    LIVE = 1
    RECORDING = 2
    NOTHING = 3

class SoftwareEngineerPerformance(Observer):
    BOOTUP_REPEATS = 4
    DEFAULT_BPM = 20
    FLICKER_DURATION = (0.5, 0.75)
    FLICKER_DELAY = (0.1, 0.5)
    FLICKER_CLOSE_TIMES = 5
    ONE_MINUTE = 60
    SHOW_LENGTH_SECONDS = 9 * ONE_MINUTE

    def __init__(self, simulate):
        Observer.__init__(self)
        self.simulate = simulate
        self.app = QApplication([])
        self.appState = AppState(self.app)
        self.cameraState = CameraState.NOTHING
        self.lastCameraState = None
        self.actionFactory = ActionFactory(self.simulate)
        self.timerFactory = TimerFactory(self.simulate)
        self.frameTimer = MagicClass('FrameTimer') if self.simulate else None
        self.videoCapture = cv2.VideoCapture(0)
        self.frame = None
        self.mockFrame = cv2.imread('cat.jpg')
        self.videoStream = VideoStream(self.videoCapture) if not self.simulate else MockVideoStream('VideoStream', self.mockFrame)
        self.link = LinkToPy.LinkInterface('/Applications/Carabiner') if not self.simulate else MockLink()
        self.abletonSet = live.Set() if not self.simulate else MockSet()
        self.ableton = Ableton(self.link, self.abletonSet, self.simulate)
        self.ableton.setBpm(SoftwareEngineerPerformance.DEFAULT_BPM)
        self.ableton.start()
        self.timeline = Timeline(self.ableton) if not self.simulate else MockTimeline(self.ableton)
        try:
            self.lightboard = DmxLightboard('/dev/cu.usbserial-6A3MRKF6')
        except Exception as e:
            self.lightboard = Lightboard()
            print(str(e))
        self.lightboard.addFixture('spot1', ChauvetOvationE910FC(dmx=self.lightboard, startChannel=4) if not self.simulate else MagicClass('spot1'))
        self.lightboard.addFixture('spot2', ChauvetOvationE910FC(dmx=self.lightboard, startChannel=61) if not self.simulate else MagicClass('spot2'))
        self.lightboard.addFixture('par38', [Par38(self.lightboard, channel) if not self.simulate else MagicClass('Par38.%d' % channel) for channel in [221, 226, 11, 16, 31, 96, 91, 86, 46, 71]])
        self.lightboard.addFixture('par64', [Par64(self.lightboard, channel) if not self.simulate else MagicClass('Par64.%d' % channel) for channel in [121, 126, 131, 136, 116, 111, 101, 139, 142]])
        self.spot1 = self.lightboard.getFixture('spot1')
        self.spot2 = self.lightboard.getFixture('spot2')
        self.par38 = self.lightboard.getFixture('par38')
        self.par64 = self.lightboard.getFixture('par64')
        self.videoArchive = VideoArchive() if not self.simulate else MockVideoArchive('VideoArchive', self.mockFrame)
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0002-empty.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0003-se1.mov')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0004-se2.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0005-sandals.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0006-tracksuit.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0007-underwear.mp4')
        self.appWindow = AppWindow()
        self.observe('appTimerUpdate', self.update)
        self.observe('startPerformance', self.startPerformance)
        self.observe('stopPerformance', self.stopPerformance)
        self.observe('scanAbletonSet', self.scanAbletonSet)
        self.observe('saveAbletonSet', self.saveAbletonSet)
        self.observe('quit', self.quit)
        self.appWindow.showFullScreen()

        if simulate:
            self.appWindow.frame = self.mockFrame
            self.startPerformance()
            while not self.timeline.isEmpty():
                self.appWindow.update()
            exit(0)

        self.app.exit(self.app.exec_())

    def update(self):
        self.timeline.update()
        self.lightboard.update()
        self.handleCameraState(self.cameraState)

    def startPerformance(self):
        self.resetAbletonSettingsToStart()
        self.blackoutLights()
        self.ableton.play()
        self.ableton.waitForNextBeat()
        if not self.simulate:
            self.appWindow.startAppTimer()
        self.bootup()

    def bootup(self):
        self.playClip('mac', trackName='bootup')
        self.playVideoArchive()
        self.setTrackVolume('furnace hum', Ableton.ZERO_DB * 0.75)
        self.playClip('furnace hum')
        self.cueIn(Seconds(self.flickerEverything()), self.lightsDoneFlickering)

    def lightsDoneFlickering(self):
        self.blackoutLights()
        self.randomlyChooseToDisplayCameraOrVideoArchiveOnInterval()
        self.fadeFixture(self.spot1, self.ableton.beatsToSeconds(4 * SoftwareEngineerPerformance.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE)
        self.fadeFixture(self.spot2, self.ableton.beatsToSeconds(4 * SoftwareEngineerPerformance.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE)
        self.pingPongBootup(Ableton.ZERO_DB)

    def pingPongBootup(self, bootupVolume: float = Ableton.ZERO_DB):
        if bootupVolume < math.pow(0.75, SoftwareEngineerPerformance.BOOTUP_REPEATS) * Ableton.ZERO_DB:
            self.normalOperations()
            return
        self.setTrackVolume('bootup', bootupVolume)
        self.playClip('mac', trackName='bootup')
        self.flicker(self.ableton.beatsToSeconds(4))
        self.cueIn(Beats(4), lambda: self.pingPongBootup(bootupVolume * 0.75))

    def normalOperations(self):
        self.setCameraState(CameraState.RECORDING)
        self.playClip('Modular UI')
        self.playClip('sin')
        self.playClip('muffle')
        self.playClip('1', trackName='moody piano')
        self.playClip('1', trackName='guitar')
        self.playClip('tech bro 1', trackName='dreams tonite')
        self.flickerFixtureRandomlyUntil(self.spot1, 8 * SoftwareEngineerPerformance.ONE_MINUTE)
        self.cueIn(Seconds(SoftwareEngineerPerformance.ONE_MINUTE + 10), self.sweepAndFlicker)
        self.cueIn(Seconds(3 * SoftwareEngineerPerformance.ONE_MINUTE), self.playCopywold)
        self.cueIn(Seconds(3 * SoftwareEngineerPerformance.ONE_MINUTE), self.crashFakeout)
        self.cueIn(Seconds(6 * SoftwareEngineerPerformance.ONE_MINUTE), self.playOfficeSpacePrinter)
        self.cueIn(Seconds(7 * SoftwareEngineerPerformance.ONE_MINUTE), lambda: self.playClip('5', trackName='grand piano'))
        self.cueIn(Seconds(8 * SoftwareEngineerPerformance.ONE_MINUTE), self.shutdown)
        self.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 6), self.getFadeFixtureAction(self.spot1, 5, DmxLightboard.MAX_VALUE, 0))
        self.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 6), self.getFadeFixtureAction(self.spot2, 5, DmxLightboard.MAX_VALUE, 0))
        self.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS), self.getFilterSweepMasterAction(1, Ableton.MAX_FILTER_FREQUENCY, Ableton.MIN_FILTER_FREQUENCY))
        self.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 1), lambda: self.toggleAudioVisual(False))
        self.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS), self.stopPerformance)

    def playCopywold(self):
        self.setTrackVolume('sin', Ableton.ZERO_DB * 0.5)
        self.setTrackVolume('guitar', Ableton.ZERO_DB * 0.5)
        self.playClip('hihats L')
        self.playClip('hihats R')
        self.playTestTrackAndFadeToZero()

    def crashFakeout(self):
        def setBpmAndRestartFrameTimer(newBpm):
            self.setBpm(newBpm)
            self.setTimerToBpm(newBpm)
        bpmList = [40, 80, 120, 240, 240, 240, 40]
        setBpmAndRestartFrameTimer(40)
        for i in range(len(bpmList)):
            def _setBpm(newBpm):
                return lambda: setBpmAndRestartFrameTimer(newBpm)
            self.cueIn(Beats((i + 1) * 8), _setBpm(bpmList[i]))
        self.cueIn(Beats(4), lambda: self.playClip('808'))
        self.cueIn(Beats(len(bpmList) * 8 - 2), lambda: self.playClip('error', trackName='windows'))
        self.cueIn(Beats(len(bpmList) * 8 - 1), lambda: self.playClip('error', trackName='windows'))
        self.cueIn(Beats(len(bpmList) * 8), lambda: self.muteEffect(Beats(8)))
        self.cueIn(Beats(len(bpmList) * 8 + 8), lambda: self.playClip('restart from crash'))
        self.cueIn(Beats(len(bpmList) * 8 + 8), lambda: self.setCameraState(CameraState.RECORDING))
        self.cueIn(Beats(len(bpmList) * 8 + 9), lambda: self.setCameraState(CameraState.RECORDING))
        self.cueIn(Beats(len(bpmList) * 8 + 10), lambda: self.setCameraState(CameraState.RECORDING))

    def playOfficeSpacePrinter(self):
        self.setCameraState(CameraState.RECORDING)
        self.setTrackVolume('sin', Ableton.ZERO_DB * 0.5)
        self.setTrackVolume('guitar', Ableton.ZERO_DB * 0.5)
        self.setBpm(20)
        self.playSpacefolderAndFadeToZero()
        self.setTrackVolume('Wavetable Bounced', Ableton.ZERO_DB * 0.8)
        self.playClip('Wavetable Bounced')
        self.playClip('Office Space Printer')
        self.playClip('tech bro 2', trackName='dreams tonite')
        self.playClip('1', trackName='slack')
        self.playClip('1', trackName='slack')
        self.cueIn(Beats(20), lambda: self.playClip('2', trackName='slack'))
        self.cueIn(Beats(40), lambda: self.playClip('3', trackName='slack'))
        self.cueIn(Seconds(30), self.sweepAndFlicker)
        self.cueIn(Seconds(60), self.restartWavetable)

    def restartWavetable(self):
        self.playClip('Wavetable Bounced')
        self.flicker(4)
        self.cueIn(Seconds(4), lambda: self.revertCameraState())

    def shutdown(self):
        fadeVolumeToQuietDuration = 25
        fadeVolumeOutDuration = 5
        quiet = Ableton.ZERO_DB * 0.45
        self.fadeVolume(self.getGroup('=Office Space Printer'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet)
        self.fadeVolume(self.getGroup('=Copywold'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet)
        self.fadeVolume(self.getGroup('=Ambient Foley'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet)
        self.fadeVolume(self.getGroup('=Beats'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet)
        self.cueIn(Seconds(fadeVolumeToQuietDuration), self.getFadeVolumeAction(self.getGroup('=Office Space Printer'), fadeVolumeOutDuration, quiet, 0))
        self.cueIn(Seconds(fadeVolumeToQuietDuration), self.getFadeVolumeAction(self.getGroup('=Copywold'), fadeVolumeOutDuration, quiet, 0))
        self.cueIn(Seconds(fadeVolumeToQuietDuration), self.getFadeVolumeAction(self.getGroup('=Ambient Foley'), fadeVolumeOutDuration, quiet, 0))
        self.cueIn(Seconds(fadeVolumeToQuietDuration), self.getFadeVolumeAction(self.getGroup('=Beats'), fadeVolumeOutDuration, quiet, 0))

    def stopPerformance(self):
        print('performance complete!')
        self.videoArchive.stop()
        self.ableton.stop()
        self.timeline.stop()
        self.appWindow.stopAppTimer()

    def handleCameraState(self, cameraState):
        if cameraState == CameraState.RECORDING:
            self.appWindow.displayFrame(self.videoArchive.getFrame())
        elif cameraState == CameraState.LIVE:
            self.appWindow.displayFrame(self.frame)
        elif cameraState == CameraState.NOTHING:
            self.appWindow.clearFrame()

    def resetAbletonSettingsToStart(self):
        self.setBpm(20)
        self.setMasterAutoFilterFrequency(Ableton.MAX_FILTER_FREQUENCY)
        self.ableton.stopAllClips()
        self.ableton.zeroAllTrackVolumes()

    def blackoutLights(self):
        self.lightboard.blackout()

    def setMasterAutoFilterFrequency(self, value):
        self.ableton.getTrack('Master').get_device('Auto Filter').get_parameter_by_name('Frequency').value = value

    def sweepAndFlicker(self):
        self.sweepEffect()
        self.flicker(4)
        self.cueIn(Seconds(4), lambda: self.revertCameraState())

    def flickerEverything(self):
        end = 0
        for fixture in random.sample(self.par38 + self.par64, 11):
            end = max(end, self.flickerFixtureRandomly(fixture, random.randint(1, 20)))
        return end

    def toggleAudioVisual(self, enabled):
        if enabled:
            self.setMasterFilterFrequency(Ableton.MAX_FILTER_FREQUENCY)
            self.revertCameraState()
        else:
            self.setMasterFilterFrequency(0)
            self.setCameraState(CameraState.NOTHING)

    def muteEffect(self, duration):
        self.toggleAudioVisual(False)
        self.cueIn(duration, lambda: self.toggleAudioVisual(True))

    def sweepEffect(self):
        # time it takes to enter effect
        sweepDuration = 0.8
        # when the fixture will turn on and off
        flickerFixture = sweepDuration + 1.0
        # when we reset back to normal
        reentry = sweepDuration + 3.0
        reentryDuration = sweepDuration * 2
        # bottom end of master frequency
        minFrequency = 0.5 * Ableton.MAX_FILTER_FREQUENCY
        # filter sweep master MAX to 0.5 * MAX
        self.filterSweepMaster(sweepDuration, Ableton.MAX_FILTER_FREQUENCY, minFrequency)
        # fade out lights
        self.fadeFixture(self.spot1, sweepDuration, DmxLightboard.MAX_VALUE, 0)
        self.fadeFixture(self.spot2, sweepDuration, DmxLightboard.MAX_VALUE, 0)
        # flash a light
        self.cueIn(Seconds(flickerFixture), lambda: self.flickerFixture(self.spot1, 0.5))
        self.cueIn(Seconds(flickerFixture), lambda: self.flickerFixture(self.spot2, 0.5))
        # filter sweep master 0.5 * MAX to MAX
        self.cueIn(Seconds(reentry), self.getFilterSweepMasterAction(reentryDuration, minFrequency, Ableton.MAX_FILTER_FREQUENCY))
        # fade in lights
        self.cueIn(Seconds(reentry), self.getFadeFixtureAction(self.spot1, reentryDuration, 0, DmxLightboard.MAX_VALUE))
        self.cueIn(Seconds(reentry), self.getFadeFixtureAction(self.spot2, reentryDuration, 0, DmxLightboard.MAX_VALUE))
        return reentry + reentryDuration

    def randomlyChooseToDisplayCameraOrVideoArchiveOnInterval(self):
        length = Beats(3)
        action = SimpleAction(lambda: self.randomlyChooseToDisplayCameraOrVideoArchiveOnInterval())
        action.isCycleAction = True
        self.cueIn(length, action)
        index = self.videoArchive.next()
        if index == 0 and self.cameraState == CameraState.RECORDING:
            choice = random.choice([CameraState.RECORDING] * 3 + [CameraState.LIVE])
            if choice == CameraState.LIVE:
                def backToRecording():
                    if self.cameraState != CameraState.NOTHING:
                        self.setCameraState(CameraState.RECORDING)
                self.cueIn(length, backToRecording)
                self.stream()

    def setBeatRepeat(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Beat Repeat').enabled = enabled

    def setPingPong(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Ping Pong').enabled = enabled

    def setFreeze(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Ping Pong').get_parameter_by_name('Freeze').value = 1 if enabled else 0

    def flickerOnFixture(self, fixture, flickerTimes):
        t = self.flickerFixtureRandomly(fixture, flickerTimes)
        self.cueIn(Seconds(t), lambda: fixture.fullOn())
        return t

    def fadeVolume(self, track, durationSeconds: float, startLevel: float, endLevel: float):
        self.cue(self.getFadeVolumeAction(track, durationSeconds, startLevel, endLevel))

    def getFadeVolumeAction(self, track, durationSeconds: float, startLevel: float, endLevel: float):
        def updateFunction(value):
            track.volume = value
        return self.actionFactory.makeLerpAction(durationSeconds, updateFunction, startLevel, endLevel)

    def flickerFixtureRandomlyUntil(self, fixture, end, minStride=15, maxStride=ONE_MINUTE):
        t = minStride
        while t < end:
            self.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, 0.3))
            t += random.uniform(minStride, maxStride)

    def flickerFixtureRandomly(self, fixture, times=1):
        t = 0.0
        for i in range(times):
            durationSeconds = random.uniform(SoftwareEngineerPerformance.FLICKER_DURATION[0], SoftwareEngineerPerformance.FLICKER_DURATION[1])
            self.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, durationSeconds))
            delaySeconds = random.uniform(SoftwareEngineerPerformance.FLICKER_DELAY[0], SoftwareEngineerPerformance.FLICKER_DELAY[1])
            t += durationSeconds + delaySeconds
        return t

    def flickerFixture(self, fixture, durationSeconds):
        oldValues = fixture.values()
        fixture.fractional(0.75)
        self.cueIn(Seconds(durationSeconds), lambda: fixture.set(oldValues))

    def fadeFixture(self, fixture, durationSeconds, startLevel, endLevel):
        self.cue(self.getFadeFixtureAction(fixture, durationSeconds, startLevel, endLevel))

    def getFadeFixtureAction(self, fixture, durationSeconds, startLevel, endLevel):
        def updateFunction(value):
            value = int(value)
            fixture.dimmer = value
            fixture.red = value
            fixture.green = value
            fixture.blue = value
            fixture.amber = value
        return self.actionFactory.makeLerpAction(durationSeconds, updateFunction, startLevel, endLevel)

    def setMasterFilterFrequency(self, frequency):
        frequency = self.ableton.clampFilterFrequency(frequency)
        self.ableton.getTrack('Master').get_device('Auto Filter').get_parameter_by_name('Frequency').value = frequency

    def filterSweepMaster(self, durationSeconds, startValue, endValue):
        self.cue(self.getFilterSweepMasterAction(durationSeconds, startValue, endValue))

    def getFilterSweepMasterAction(self, durationSeconds: float, startValue: float, endValue: float):
        def updateFunction(value):
            self.setMasterFilterFrequency(value)
        return self.actionFactory.makeLerpAction(durationSeconds, updateFunction, startValue, endValue)

    def setTimerToBpm(self, newBpm):
        self.executeOnUiThread(lambda: self.timerFactory.restart(self.ableton.millisecondsPerBeat(newBpm)))

    def playVideoArchive(self):
        self.executeOnUiThread(lambda: self.videoArchive.play())

    def flicker(self, delaySeconds: float = 4):
        def uiThreadOperations():
            print('flickering {}'.format(delaySeconds))
            self.setCameraState(CameraState.LIVE)
            self.videoStream.setDelaySeconds(delaySeconds)
            self.videoStream.start()
            self.streamVideoToScreen()
        self.executeOnUiThread(uiThreadOperations)

    def stream(self):
        def uiThreadOperations():
            def onTimeout():
                self.frame = self.videoStream.getLast()
            self.setCameraState(CameraState.LIVE)
            milliseconds = MILLISECONDS_IN_SECOND / (self.videoStream.getMaxFps())
            self.timerFactory.makeGlobalFrameTimer(milliseconds, onTimeout)
        self.executeOnUiThread(uiThreadOperations)

    def executeOnUiThread(self, function):
        self.appWindow.executeOnUiThread(function)

    def streamVideoToScreen(self):
        def onTimeout():
            self.frame = self.videoStream.getHead()
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoStream.getMaxFps())
        self.timerFactory.makeGlobalFrameTimer(milliseconds, onTimeout)

    def playTestTrackAndFadeToZero(self):
        track = self.getTrack('test')
        startVol = Ableton.ZERO_DB * 0.5
        track.volume = startVol
        track.play_clip(name='tone')
        self.fadeVolume(track, 30, startVol, Ableton.ZERO_DB)

    def playSpacefolderAndFadeToZero(self):
        spacefolder = self.getTrack('Spacefolder Bounced')
        spacefolder.volume = Ableton.ZERO_DB * 0.5
        spacefolder.play_clip(name='1')
        self.fadeVolume(spacefolder, 10, spacefolder.volume, Ableton.ZERO_DB)

    def setBpm(self, bpm):
        self.ableton.setBpm(bpm)

    def getTrack(self, trackName):
        return self.ableton.getTrack(trackName)

    def getGroup(self, groupName):
        return self.ableton.getGroup(groupName)

    def cue(self, action):
        self.timeline.cue(action)

    def cueIn(self, duration, action):
        self.timeline.cueIn(duration, action)

    def cueFunction(self, function):
        def wrapped():
            self.timeline.cue(function)
        return wrapped

    def playClip(self, name, trackName=None):
        self.ableton.playClip(name, trackName)

    def setTrackVolume(self, trackName, value):
        self.ableton.getTrack(trackName).volume = value

    def setCameraState(self, state):
        print('setCameraState({})'.format(state))
        self.lastCameraState = self.cameraState
        self.cameraState = state

    def revertCameraState(self):
        self.cameraState = self.lastCameraState

    def scanAbletonSet(self):
        self.ableton.scan()

    def saveAbletonSet(self):
        self.ableton.set.save()

    def quit(self):
        self.appWindow.quit()
        self.timerFactory.stop()
        self.videoStream.cleanup()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.stopAllClips()
        self.ableton.cleanup()
        self.ableton.join()
        self.videoArchive.cleanup()
        self.appState.quit()