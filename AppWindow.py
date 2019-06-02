from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pyCreative import *
import cv2
import live
import math
import random
from VideoArchive import VideoArchive

frame_width = 1280
frame_height = 720
MILLISECONDS_IN_SECOND = 1000.0
UPDATES_PER_SECOND = 300.0

from enum import Enum
class DrawState(Enum):
    LIVE = 1
    RECORDING = 2
    NOTHING = 3

class AppWindow(QMainWindow):
    BOOTUP_REPEATS = 4
    FLICKER_DURATION = (0.5, 0.75)
    FLICKER_DELAY = (0.1, 0.5)
    FLICKER_CLOSE_TIMES = 5
    ONE_MINUTE = 60
    SHOW_LENGTH_SECONDS = 9 * ONE_MINUTE
    DEFAULT_BPM = 20

    def __init__(self, appState, parent=None):
        QWidget.__init__(self, parent)
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.setBackgroundColor(Qt.black)
        self.imageView = QLabel(centralWidget)
        self.appState = appState
        self.capture = cv2.VideoCapture(0)
        self.videoBuffer = VideoBuffer(self.capture, 300)
        self.videoBuffer.start()
        self.videoHeader = VideoHeader(self.videoBuffer)
        self.frame = None
        self.appTimer = None
        self.frameTimer = None
        self.ableton = Ableton()
        self.ableton.setBpm(AppWindow.DEFAULT_BPM)
        self.ableton.start()
        self.timeline = Timeline(self.ableton)
        self.lightboard = None
        try:
            self.lightboard = DmxLightboard('/dev/cu.usbserial-6A3MRKF6')
        except Exception as e:
            print(str(e))
            self.lightboard = GenericLightboard()
        self.spot1 = ChauvetOvationE910FC(dmx=self.lightboard, startChannel=4) #76
        self.spot2 = ChauvetOvationE910FC(dmx=self.lightboard, startChannel=61) #51
        self.par38 = [Par38(self.lightboard, channel) for channel in [221, 226, 11, 16, 31, 96, 91, 86, 46, 71]]
        self.par64 = [Par64(self.lightboard, channel) for channel in [121, 126, 131, 136, 116, 111, 101, 139, 142]]
        self.uiThreadFunctions = []
        self.drawFrames = False
        self.videoArchive = VideoArchive()
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0002-empty.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0003-se1.mov')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0004-se2.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0005-sandals.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0006-tracksuit.mp4')
        self.videoArchive.append('/Users/admin/Dropbox/Software Engineer/C0007-underwear.mp4')
        self.drawState = DrawState.NOTHING
        self.lastDrawState = None

    def setDrawState(self, state):
        print('setDrawState({})'.format(state))
        self.lastDrawState = self.drawState
        self.drawState = state
    def revertDrawState(self):
        self.drawState = self.lastDrawState

    def startAppTimer(self):
        self.appTimer = QTimer()
        self.appTimer.timeout.connect(self.update)
        timeout = MILLISECONDS_IN_SECOND / UPDATES_PER_SECOND
        self.appTimer.start(timeout)

    def stopAppTimer(self):
        if self.appTimer is not None:
            self.appTimer.stop()

    def start(self):
        self.ableton.play()
        self.startAppTimer()

    def stop(self):
        self.ableton.stop()
        self.stopAppTimer()

    def update(self):
        for f in self.uiThreadFunctions:
            f()
        self.uiThreadFunctions = []
        self.timeline.update()
        self.lightboard.update()
        if self.drawState == DrawState.RECORDING:
            self.setCv2Frame(self.videoArchive.getFrame())
        elif self.drawState == DrawState.LIVE and self.frame is not None:
            self.setCv2Frame(self.frame)
        elif self.drawState == DrawState.NOTHING:
            self.imageView.clear()

    def executeOnUiThread(self, f):
        self.uiThreadFunctions.append(f)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Q:
            self.quit()
        elif key == Qt.Key_BracketLeft:
            self.stop()
        elif key == Qt.Key_BracketRight:
            self.start()
        elif key == Qt.Key_F:
            self.flicker(0)
        elif key == Qt.Key_J:
            self.jitter()
        elif key == Qt.Key_N:
            self.stream()
        elif key == Qt.Key_Semicolon:
            self.ableton.scan()
        elif key == Qt.Key_Apostrophe:
            self.ableton.set.save()
        elif key == Qt.Key_T:
            self.test()
        elif key == Qt.Key_A:
            self.setDrawState(DrawState.RECORDING)
            if not self.videoArchive.playing:
                self.videoArchive.play()
        elif key == Qt.Key_Right:
            self.setDrawState(DrawState.RECORDING)
            self.videoArchive.next()
        elif key == Qt.Key_Left:
            self.setDrawState(DrawState.RECORDING)
            self.videoArchive.previous()
        elif key == Qt.Key_V:
            value = 255
            self.lightboard.blackout()
            self.spot1.dimmer = value
            self.spot1.red = value
            self.spot1.green = value
            self.spot1.blue = value
            self.spot1.amber = value
            self.spot2.dimmer = value
            self.spot2.red = value
            self.spot2.green = value
            self.spot2.blue = value
            self.spot2.amber = value
        elif key == Qt.Key_B:
            self.lightboard.blackout()
        elif key == Qt.Key_Y:
            self.secondaryTest()
        elif key == Qt.Key_U:
            self.thirdTest()
        elif key == Qt.Key_O:
            self.stopPerformance()
        elif key == Qt.Key_P:
            self.startPerformance()

    def thirdTest(self):
        def stopTest():
            self.setDrawState(DrawState.NOTHING)
            self.stop()
        self.start()
        self.ableton.playClip('Modular UI')
        self.ableton.setBpm(60)
        self.setDrawState(DrawState.RECORDING)
        self.executeOnUiThread(lambda: self.videoArchive.play())
        self.cycleVideoStreams()
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS), lambda: stopTest())

    def secondaryTest(self):
        def stopTest():
            self.setDrawState(DrawState.NOTHING)
            self.stop()
        self.start()
        self.flickerFixtureRandomlyUntil(self.spot1, 10)
        self.flickerFixtureRandomlyUntil(self.spot2, 10)
        self.executeOnUiThread(f=lambda: self.stream())
        self.ableton.playClip('official test')
        self.timeline.cueIn(Seconds(4), lambda: self.muteEffect(Seconds(4)))
        self.timeline.cueIn(Seconds(10), lambda: stopTest())

    def startPerformance(self):
        self.ableton.setBpm(20)
        self.lightboard.blackout()
        self.ableton.getTrack('Master').get_device('Auto Filter').get_parameter_by_name('Frequency').value = Ableton.MAX_FILTER_FREQUENCY
        self.ableton.stopAllClips()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.play()
        self.ableton.waitForNextBeat()
        self.startAppTimer()
        self.bootup()

    def stopPerformance(self):
        print('performance complete!')
        self.videoArchive.stop()
        self.ableton.stop()
        self.timeline.stop()
        self.stopAppTimer()

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
            self.setDrawState(DrawState.NOTHING)
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
        if index == 0 and self.drawState == DrawState.RECORDING:
            choice = random.choice([DrawState.RECORDING] * 3 + [DrawState.LIVE])
            if choice == DrawState.LIVE:
                def backToRecording():
                    if self.drawState != DrawState.NOTHING:
                        self.setDrawState(DrawState.RECORDING)
                self.timeline.cueIn(length, backToRecording)
                self.executeOnUiThread(lambda: self.stream())
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
        return LerpAction(durationSeconds, updateFunction, startLevel, endLevel)
    def flickerFixtureRandomlyUntil(self, fixture, end, minStride=15, maxStride=ONE_MINUTE):
        random.seed()
        t = minStride
        while t < end:
            self.timeline.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, 0.3))
            t += random.uniform(minStride, maxStride)
    def flickerFixtureRandomly(self, fixture, times=1):
        t = 0.0
        for i in range(times):
            random.seed()
            durationSeconds = random.uniform(AppWindow.FLICKER_DURATION[0], AppWindow.FLICKER_DURATION[1])
            self.timeline.cueIn(Seconds(t), lambda: self.flickerFixture(fixture, durationSeconds))
            delaySeconds = random.uniform(AppWindow.FLICKER_DELAY[0], AppWindow.FLICKER_DELAY[1])
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
        return LerpAction(durationSeconds, updateFunction, startLevel, endLevel)
    def setMasterFilterFrequency(self, frequency):
        frequency = self.ableton.clampFilterFrequency(frequency)
        self.ableton.getTrack('Master').get_device('Auto Filter').get_parameter_by_name('Frequency').value = frequency
    def filterSweepMaster(self, durationSeconds: float, startValue: float, endValue: float):
        def updateFunction(value):
            self.setMasterFilterFrequency(value)
        return LerpAction(durationSeconds, updateFunction, startValue, endValue)

    def bootup(self):
        def pingPongBootup(bootupVolume: float = Ableton.ZERO_DB):
            if bootupVolume < math.pow(0.75, AppWindow.BOOTUP_REPEATS) * Ableton.ZERO_DB:
                self.normalOperations()
                return
            self.ableton.getTrack('bootup').volume = bootupVolume
            self.bootupSound()
            self.executeOnUiThread(lambda: self.flicker(self.ableton.beatsToSeconds(4)))
            self.timeline.cueIn(Beats(4), lambda: pingPongBootup(bootupVolume * 0.75))
        self.bootupSound()
        self.executeOnUiThread(lambda: self.videoArchive.play())
        self.ableton.getTrack('furnace hum').volume = Ableton.ZERO_DB * 0.75
        self.ableton.playClip('furnace hum')
        t = Seconds(self.flickerEverything())
        self.timeline.cueIn(t, lambda: self.lightboard.blackout())
        self.timeline.cueIn(t, lambda: self.cycleVideoStreams())
        self.timeline.cueIn(t, lambda: pingPongBootup(Ableton.ZERO_DB))
        self.timeline.cueIn(t, self.fadeFixture(self.spot1, self.ableton.beatsToSeconds(4 * AppWindow.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE))
        self.timeline.cueIn(t, self.fadeFixture(self.spot2, self.ableton.beatsToSeconds(4 * AppWindow.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE))

    def normalOperations(self):
        self.setDrawState(DrawState.RECORDING)
        self.timeline.cue(lambda: self.ableton.playClip('Modular UI'))
        self.timeline.cue(lambda: self.ableton.playClip('sin'))
        self.timeline.cue(lambda: self.ableton.playClip('muffle'))
        self.timeline.cue(lambda: self.ableton.getTrack('moody piano').play_clip(name='1'))
        self.timeline.cue(lambda: self.ableton.getTrack('guitar').play_clip(name='1'))
        self.timeline.cue(lambda: self.ableton.getTrack('dreams tonite').play_clip(name='tech bro 1'))
        self.timeline.cueIn(Seconds(AppWindow.ONE_MINUTE + 10), self.sweepAndFlicker)
        self.flickerFixtureRandomlyUntil(self.spot1, 8 * AppWindow.ONE_MINUTE)
        self.timeline.cueIn(Seconds(3 * AppWindow.ONE_MINUTE), self.playCopywold)
        self.timeline.cueIn(Seconds(6 * AppWindow.ONE_MINUTE), self.playOfficeSpacePrinter)
        self.timeline.cueIn(Seconds(7 * AppWindow.ONE_MINUTE), lambda: self.playPiano(5))
        self.timeline.cueIn(Seconds(8 * AppWindow.ONE_MINUTE), self.shutdown)
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS - 6), self.fadeFixture(self.spot1, 5, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS - 6), self.fadeFixture(self.spot2, 5, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS), self.filterSweepMaster(1, Ableton.MAX_FILTER_FREQUENCY, Ableton.MIN_FILTER_FREQUENCY))
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS - 1), lambda: self.toggleAudioVisual(False))
        self.timeline.cueIn(Seconds(AppWindow.SHOW_LENGTH_SECONDS), self.stopPerformance)

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

    def playCopywold(self):
        def setBpm(bpm):
            self.ableton.setBpm(bpm)
            self.executeOnUiThread(lambda: self.frameTimer.start(self.ableton.millisecondsPerBeat(bpm)))
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
            self.timeline.cueIn(Beats(len(bpm) * 8 + 8), lambda: self.setDrawState(DrawState.RECORDING))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 9), lambda: self.setDrawState(DrawState.RECORDING))
            self.timeline.cueIn(Beats(len(bpm) * 8 + 10), lambda: self.setDrawState(DrawState.RECORDING))
        def intro():
            setBpm(40)
            self.ableton.getTrack('sin').volume = Ableton.ZERO_DB * 0.5
            self.ableton.getTrack('guitar').volume = Ableton.ZERO_DB * 0.5
            self.ableton.playClip('hihats L')
            self.ableton.playClip('hihats R')
            self.timeline.cueIn(Beats(4), lambda: self.ableton.playClip('808'))
            body()
        intro()

    def sweepAndFlicker(self):
        self.sweepEffect()
        self.executeOnUiThread(lambda: self.flicker(4))
        self.timeline.cueIn(Seconds(4), lambda: self.revertDrawState())
    def playOfficeSpacePrinter(self):
        def restartWavetable():
            self.ableton.playClip('Wavetable Bounced')
            self.executeOnUiThread(lambda: self.flicker(4))
            self.timeline.cueIn(Seconds(4), lambda: self.revertDrawState())
        self.setDrawState(DrawState.RECORDING)
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

    def playGrandPianoFinale(self):
        self.ableton.getTrack('grand piano').play_clip(name='5')

    def stopVideo(self):
        if self.frameTimer is not None:
            self.frameTimer.stop()
            self.frameTimer = None
    def test(self):
        def stopTest():
            self.stopVideo()
            self.setDrawState(DrawState.NOTHING)
        testLength = 10
        self.ableton.stopAllClips()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.play()
        officalTestTrack = self.ableton.getTrack('official test')
        officalTestTrack.play_clip(name='official test')
        self.timeline.cue(lambda: self.flickerFixtureRandomly(self.spot1, times=5))
        self.timeline.cue(self.fadeVolume(officalTestTrack, 0, Ableton.ZERO_DB))
        self.timeline.cueIn(Seconds(testLength/2), self.fadeVolume(officalTestTrack, testLength/2, Ableton.ZERO_DB, 0))
        self.timeline.cue(self.fadeFixture(self.spot1, testLength/2, 0, DmxLightboard.MAX_VALUE))
        self.timeline.cueIn(Seconds(testLength/2), self.fadeFixture(self.spot1, testLength/2, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueIn(Seconds(testLength), stopTest)
        self.executeOnUiThread(lambda: self.stream())

    def flicker(self, delaySeconds: float = 4):
        print('flickering {}'.format(delaySeconds))
        self.setDrawState(DrawState.LIVE)
        self.videoHeader.setDelaySeconds(delaySeconds)
        self.videoHeader.start()
        self.streamVideoHeader(self.videoHeader)
    def streamVideoHeader(self, videoHeader):
        def onTimeout():
            self.frame = videoHeader.getHead()
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoBuffer.get_max_fps())
        self.makeGlobalFrameTimer(milliseconds, onTimeout)
    def stream(self):
        print('stream')
        def onTimeout():
            self.frame = self.videoBuffer.get_last()
        self.setDrawState(DrawState.LIVE)
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoBuffer.get_max_fps())
        self.makeGlobalFrameTimer(milliseconds, onTimeout)
    def jitter(self, tickMilliseconds: float = 150.0):
        print('jitter {}'.format(tickMilliseconds))
        def onTimeout():
            self.frame = self.videoBuffer.get_last()
        self.setDrawState(DrawState.LIVE)
        self.makeGlobalFrameTimer(tickMilliseconds, onTimeout)
    def makeLocalFrameTimer(self, milliseconds, onTimeout):
        localFrameTimer = QTimer()
        localFrameTimer.timeout.connect(onTimeout)
        localFrameTimer.start(int(milliseconds))
        return localFrameTimer
    def makeGlobalFrameTimer(self, milliseconds, onTimeout):
        if self.frameTimer is not None:
            self.frameTimer.stop()
        self.frameTimer = QTimer()
        self.frameTimer.timeout.connect(onTimeout)
        self.frameTimer.start(int(milliseconds))

    def setBackgroundColor(self, color):
        palette = self.palette()
        palette.setColor(self.backgroundRole(), color)
        self.setPalette(palette)

    def closeEvent(self, event):
        self.quit()

    def quit(self):
        if self.appTimer is not None:
            self.appTimer.stop()
        if self.frameTimer is not None:
            self.frameTimer.stop()
        self.videoBuffer.cleanup()
        self.videoBuffer.join()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.stopAllClips()
        self.ableton.cleanup()
        self.ableton.join()
        self.capture.release()
        self.videoArchive.cleanup()
        self.appState.quit()

    def resizeEvent(self, event):
        scaled_width = self.width()
        ratio = scaled_width / frame_width
        scaled_height = frame_height * ratio
        self.imageView.setFixedSize(QSize(scaled_width, scaled_height))

    def setCv2Frame(self, frame):
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
