import math
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
        centralWidget = QWidget()
        imageView = QLabel(centralWidget)
        self.appWindow = AppWindow(
            centralWidget=centralWidget,
            imageView=imageView
        )
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
        if self.cameraState == CameraState.RECORDING:
            self.appWindow.displayFrame(self.videoArchive.getFrame())
        elif self.cameraState == CameraState.LIVE:
            self.appWindow.displayFrame(self.frame)
        elif self.cameraState == CameraState.NOTHING:
            self.appWindow.clearFrame()

    def startPerformance(self):
        self.ableton.setBpm(20)
        self.lightboard.blackout()
        self.ableton.getTrack('Master').get_device('Auto Filter').get_parameter_by_name('Frequency').value = Ableton.MAX_FILTER_FREQUENCY
        self.ableton.stopAllClips()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.play()
        self.ableton.waitForNextBeat()
        if not self.simulate:
            self.appWindow.startAppTimer()
        self.bootup()

    def bootup(self):
        def pingPongBootup(bootupVolume: float = Ableton.ZERO_DB):
            if bootupVolume < math.pow(0.75, SoftwareEngineerPerformance.BOOTUP_REPEATS) * Ableton.ZERO_DB:
                self.normalOperations()
                return
            self.ableton.getTrack('bootup').volume = bootupVolume
            self.bootupSound()
            self.appWindow.executeOnUiThread(lambda: self.flicker(self.ableton.beatsToSeconds(4)))
            self.timeline.cueIn(Beats(4), lambda: pingPongBootup(bootupVolume * 0.75))
        self.bootupSound()
        self.appWindow.executeOnUiThread(lambda: self.videoArchive.play())
        self.ableton.getTrack('furnace hum').volume = Ableton.ZERO_DB * 0.75
        self.ableton.playClip('furnace hum')
        t = Seconds(self.flickerEverything())
        self.timeline.cueIn(t, lambda: self.lightboard.blackout())
        self.timeline.cueIn(t, lambda: self.cycleVideoStreams())
        self.timeline.cueIn(t, lambda: pingPongBootup(Ableton.ZERO_DB))
        self.timeline.cueIn(t, self.fadeFixture(self.spot1, self.ableton.beatsToSeconds(4 * SoftwareEngineerPerformance.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE))
        self.timeline.cueIn(t, self.fadeFixture(self.spot2, self.ableton.beatsToSeconds(4 * SoftwareEngineerPerformance.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE))

    def normalOperations(self):
        self.setCameraState(CameraState.RECORDING)
        self.timeline.cue(lambda: self.ableton.playClip('Modular UI'))
        self.timeline.cue(lambda: self.ableton.playClip('sin'))
        self.timeline.cue(lambda: self.ableton.playClip('muffle'))
        self.timeline.cue(lambda: self.ableton.getTrack('moody piano').play_clip(name='1'))
        self.timeline.cue(lambda: self.ableton.getTrack('guitar').play_clip(name='1'))
        self.timeline.cue(lambda: self.ableton.getTrack('dreams tonite').play_clip(name='tech bro 1'))
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.ONE_MINUTE + 10), self.sweepAndFlicker)
        self.flickerFixtureRandomlyUntil(self.spot1, 8 * SoftwareEngineerPerformance.ONE_MINUTE)
        self.timeline.cueIn(Seconds(3 * SoftwareEngineerPerformance.ONE_MINUTE), self.playCopywold)
        self.timeline.cueIn(Seconds(6 * SoftwareEngineerPerformance.ONE_MINUTE), self.playOfficeSpacePrinter)
        self.timeline.cueIn(Seconds(7 * SoftwareEngineerPerformance.ONE_MINUTE), lambda: self.playPiano(5))
        self.timeline.cueIn(Seconds(8 * SoftwareEngineerPerformance.ONE_MINUTE), self.shutdown)
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 6), self.fadeFixture(self.spot1, 5, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 6), self.fadeFixture(self.spot2, 5, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS), self.filterSweepMaster(1, Ableton.MAX_FILTER_FREQUENCY, Ableton.MIN_FILTER_FREQUENCY))
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS - 1), lambda: self.toggleAudioVisual(False))
        self.timeline.cueIn(Seconds(SoftwareEngineerPerformance.SHOW_LENGTH_SECONDS), self.stopPerformance)

    def playCopywold(self):
        def setBpm(bpm):
            self.ableton.setBpm(bpm)
            self.appWindow.executeOnUiThread(lambda: self.timerFactory.restart(self.ableton.millisecondsPerBeat(bpm)))
        def body():
            track = self.ableton.getTrack('test')
            startVol = Ableton.ZERO_DB * 0.5
            track.volume = startVol
            track.play_clip(name='tone')
            self.timeline.cue(self.fadeVolume(track, 30, startVol, Ableton.ZERO_DB))
            bpm = [40, 80, 120, 240, 240, 240, 40]
            for i in range(len(bpm)):
                def _setBpm(bpm):
                    return lambda: setBpm(bpm)
                self.timeline.cueIn(Beats((i + 1) * 8), _setBpm(bpm[i]))
            self.timeline.cueIn(Beats(len(bpm) * 8 - 2), lambda: self.ableton.getTrack('windows').play_clip(name='error'))
            self.timeline.cueIn(Beats(len(bpm) * 8 - 1), lambda: self.ableton.getTrack('windows').play_clip(name='error'))
            self.timeline.cueIn(Beats(len(bpm) * 8), lambda: self.muteEffect(Beats(8)))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 8), lambda: self.ableton.playClip('restart from crash'))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 8), lambda: self.setCameraState(CameraState.RECORDING))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 9), lambda: self.setCameraState(CameraState.RECORDING))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 10), lambda: self.setCameraState(CameraState.RECORDING))
        def intro():
            setBpm(40)
            self.ableton.getTrack('sin').volume = Ableton.ZERO_DB * 0.5
            self.ableton.getTrack('guitar').volume = Ableton.ZERO_DB * 0.5
            self.ableton.playClip('hihats L')
            self.ableton.playClip('hihats R')
            self.timeline.cueIn(Beats(4), lambda: self.ableton.playClip('808'))
            body()
        intro()

    def playOfficeSpacePrinter(self):
        def restartWavetable():
            self.ableton.playClip('Wavetable Bounced')
            self.appWindow.executeOnUiThread(lambda: self.flicker(4))
            self.timeline.cueIn(Seconds(4), lambda: self.revertDrawState())
        self.setCameraState(CameraState.RECORDING)
        self.ableton.getTrack('sin').volume = Ableton.ZERO_DB * 0.5
        self.ableton.getTrack('guitar').volume = Ableton.ZERO_DB * 0.5
        self.ableton.setBpm(20)
        spacefolder = self.ableton.getTrack('Spacefolder Bounced')
        spacefolder.volume = Ableton.ZERO_DB * 0.5
        spacefolder.play_clip(name='1')
        self.timeline.cue(self.fadeVolume(spacefolder, 10, spacefolder.volume, Ableton.ZERO_DB))
        self.ableton.getTrack('Wavetable Bounced').volume = Ableton.ZERO_DB * 0.8
        self.ableton.playClip('Wavetable Bounced')
        self.ableton.playClip('Office Space Printer')
        self.timeline.cue(lambda: self.ableton.getTrack('dreams tonite').play_clip(name='tech bro 2'))
        clip = self.ableton.getTrack('slack').get_clip('1')
        clip.play()
        self.timeline.cueInBeats(20, lambda: self.ableton.getTrack('slack').play_clip(name='2'))
        self.timeline.cueInBeats(40, lambda: self.ableton.getTrack('slack').play_clip(name='3'))
        self.timeline.cueIn(Seconds(30), self.sweepAndFlicker)
        self.timeline.cueIn(Seconds(60), restartWavetable)

    def shutdown(self):
        fadeVolumeToQuietDuration = 25
        fadeVolumeOutDuration = 5
        quiet = Ableton.ZERO_DB * 0.45
        self.timeline.cue(self.fadeVolume(self.ableton.getGroup('=Office Space Printer'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(self.fadeVolume(self.ableton.getGroup('=Copywold'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(self.fadeVolume(self.ableton.getGroup('=Ambient Foley'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(self.fadeVolume(self.ableton.getGroup('=Beats'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cueIn(Seconds(fadeVolumeToQuietDuration), self.fadeVolume(self.ableton.getGroup('=Office Space Printer'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueIn(Seconds(fadeVolumeToQuietDuration), self.fadeVolume(self.ableton.getGroup('=Copywold'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueIn(Seconds(fadeVolumeToQuietDuration), self.fadeVolume(self.ableton.getGroup('=Ambient Foley'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueIn(Seconds(fadeVolumeToQuietDuration), self.fadeVolume(self.ableton.getGroup('=Beats'), fadeVolumeOutDuration, quiet, 0))

    def stopPerformance(self):
        print('performance complete!')
        self.videoArchive.stop()
        self.ableton.stop()
        self.timeline.stop()
        self.appWindow.stopAppTimer()

    def sweepAndFlicker(self):
        self.sweepEffect()
        self.appWindow.executeOnUiThread(lambda: self.flicker(4))
        self.timeline.cueIn(Seconds(4), lambda: self.revertDrawState())
    def playGrandPianoFinale(self):
        self.ableton.getTrack('grand piano').play_clip(name='5')
    def flickerEverything(self):
        end = 0
        for fixture in random.sample(self.par38 + self.par64, 11):
            end = max(end, self.flickerFixtureRandomly(fixture, random.randint(1, 20)))
        return end
    def toggleAudioVisual(self, enabled):
        if enabled:
            self.setMasterFilterFrequency(Ableton.MAX_FILTER_FREQUENCY)
            self.revertDrawState()
        else:
            self.setMasterFilterFrequency(0)
            self.setCameraState(CameraState.NOTHING)
    def muteEffect(self, duration):
        self.toggleAudioVisual(False)
        self.timeline.cueIn(duration, lambda: self.toggleAudioVisual(True))
    def playPiano(self, clipNumber):
        piano = self.ableton.getTrack('grand piano')
        piano.play_clip(name=str(clipNumber))
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
        self.timeline.cue(self.filterSweepMaster(sweepDuration, Ableton.MAX_FILTER_FREQUENCY, minFrequency))
        # fade out lights
        self.timeline.cue(self.fadeFixture(self.spot1, sweepDuration, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cue(self.fadeFixture(self.spot2, sweepDuration, DmxLightboard.MAX_VALUE, 0))
        # flash a light
        self.timeline.cueIn(Seconds(flickerFixture), lambda: self.flickerFixture(self.spot1, 0.5))
        self.timeline.cueIn(Seconds(flickerFixture), lambda: self.flickerFixture(self.spot2, 0.5))
        # filter sweep master 0.5 * MAX to MAX
        self.timeline.cueIn(Seconds(reentry), self.filterSweepMaster(reentryDuration, minFrequency, Ableton.MAX_FILTER_FREQUENCY))
        # fade in lights
        self.timeline.cueIn(Seconds(reentry), self.fadeFixture(self.spot1, reentryDuration, 0, DmxLightboard.MAX_VALUE))
        self.timeline.cueIn(Seconds(reentry), self.fadeFixture(self.spot2, reentryDuration, 0, DmxLightboard.MAX_VALUE))
        return reentry + reentryDuration
    def cycleVideoStreams(self):
        length = Beats(3)
        action = SimpleAction(lambda: self.cycleVideoStreams())
        action.isCycleAction = True
        self.timeline.cueIn(length, action)
        index = self.videoArchive.next()
        if index == 0 and self.cameraState == CameraState.RECORDING:
            choice = random.choice([CameraState.RECORDING] * 3 + [CameraState.LIVE])
            if choice == CameraState.LIVE:
                def backToRecording():
                    if self.cameraState != CameraState.NOTHING:
                        self.setCameraState(CameraState.RECORDING)
                self.timeline.cueIn(length, backToRecording)
                self.appWindow.executeOnUiThread(lambda: self.stream())
    def setBeatRepeat(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Beat Repeat').enabled = enabled
    def setPingPong(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Ping Pong').enabled = enabled
    def setFreeze(self, enabled: bool):
        self.ableton.getTrack('bootup').get_device('Ping Pong').get_parameter_by_name('Freeze').value = 1 if enabled else 0
    def bootupSound(self):
        self.ableton.getTrack('bootup').play_clip(name='mac')
    def setBootupVolume(self, volume):
        self.ableton.getTrack('bootup').volume = volume
    def flickerOnFixture(self, fixture, flickerTimes):
        t = self.flickerFixtureRandomly(fixture, flickerTimes)
        self.timeline.cueIn(Seconds(t), lambda: fixture.fullOn())
        return t
    def fadeVolume(self, track: live.Track, durationSeconds: float, startLevel: float, endLevel: float):
        def updateFunction(value):
            track.volume = value
        return self.actionFactory.makeLerpAction(durationSeconds, updateFunction, startLevel, endLevel)
    def flickerFixtureRandomlyUntil(self, fixture, end, minStride=15, maxStride=ONE_MINUTE):
        t = minStride
        while t < end:
            self.timeline.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, 0.3))
            t += random.uniform(minStride, maxStride)
    def flickerFixtureRandomly(self, fixture, times=1):
        t = 0.0
        for i in range(times):
            durationSeconds = random.uniform(SoftwareEngineerPerformance.FLICKER_DURATION[0], SoftwareEngineerPerformance.FLICKER_DURATION[1])
            self.timeline.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, durationSeconds))
            delaySeconds = random.uniform(SoftwareEngineerPerformance.FLICKER_DELAY[0], SoftwareEngineerPerformance.FLICKER_DELAY[1])
            t += durationSeconds + delaySeconds
        return t
    def flickerFixture(self, fixture, durationSeconds):
        oldValues = fixture.values()
        self.timeline.cue(lambda: fixture.fractional(0.75))
        self.timeline.cueIn(Seconds(durationSeconds), lambda: fixture.set(oldValues))
    def fadeFixture(self, fixture, durationSeconds, startLevel, endLevel):
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
    def filterSweepMaster(self, durationSeconds: float, startValue: float, endValue: float):
        def updateFunction(value):
            self.setMasterFilterFrequency(value)
        return self.actionFactory.makeLerpAction(durationSeconds, updateFunction, startValue, endValue)
    def flicker(self, delaySeconds: float = 4):
        print('flickering {}'.format(delaySeconds))
        self.setCameraState(CameraState.LIVE)
        self.videoStream.setDelaySeconds(delaySeconds)
        self.videoStream.start()
        self.streamVideoToScreen()
    def streamVideoToScreen(self):
        def onTimeout():
            self.frame = self.videoStream.getHead()
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoStream.getMaxFps())
        self.timerFactory.makeGlobalFrameTimer(milliseconds, onTimeout)
    def stream(self):
        print('stream')
        def onTimeout():
            self.frame = self.videoStream.getLast()
        self.setCameraState(CameraState.LIVE)
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoStream.getMaxFps())
        self.timerFactory.makeGlobalFrameTimer(milliseconds, onTimeout)

    def setCameraState(self, state):
        print('setCameraState({})'.format(state))
        self.lastCameraState = self.cameraState
        self.cameraState = state

    def revertDrawState(self):
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

performance = SoftwareEngineerPerformance(simulate)
