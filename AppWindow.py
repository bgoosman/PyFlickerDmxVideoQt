from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pyCreative import *
import cv2
import live
import math
import random

frame_width = 1280
frame_height = 720
MILLISECONDS_IN_SECOND = 1000.0
UPDATES_PER_SECOND = 300.0

class AppWindow(QMainWindow):
    BOOTUP_REPEATS = 4
    FLICKER_DURATION = (0.5, 0.75)
    FLICKER_DELAY = (0.1, 0.5)
    FLICKER_CLOSE_TIMES = 5
    ONE_MINUTE = 60
    SHOW_LENGTH_SECONDS = 9 * ONE_MINUTE

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
        self.ableton.setBpm(40)
        self.ableton.start()
        self.timeline = Timeline(self.ableton)
        self.lightboard = None
        try:
            self.lightboard = DmxLightboard('/dev/cu.usbserial-6A3MRKF6')
        except Exception as e:
            print(str(e))
            self.lightboard = GenericLightboard()
        self.spotlight = ChauvetOvationE910FC(dmx=self.lightboard, startChannel=61)
        self.spotlightClose = ChauvetOvationE910FC(dmx=self.lightboard, startChannel=51)
        self.par38 = [Par38(self.lightboard, channel) for channel in [221, 226, 11, 16, 31, 96, 91, 86, 46, 71]]
        self.par64 = [Par64(self.lightboard, channel) for channel in [121, 126, 131, 136, 116, 111, 101, 139, 142]]
        self.uiThreadFunctions = []
        self.drawFrames = True

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
        if self.frame is not None and self.drawFrames:
            self.setCv2Frame(self.frame)

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
            self.flicker()
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
        elif key == Qt.Key_B:
            self.lightboard.blackout()
        elif key == Qt.Key_Y:
            self.secondaryTest()
        elif key == Qt.Key_O:
            self.stopPerformance()
        elif key == Qt.Key_P:
            self.startPerformance()

    def secondaryTest(self):
        self.start()
        self.shutdown()

    def startPerformance(self):
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
        self.ableton.stop()
        self.timeline.stop()
        self.stopAppTimer()

    def toggleAudioVisual(self, enabled):
        if enabled:
            self.setMasterFilterFrequency(Ableton.MAX_FILTER_FREQUENCY)
            self.drawFrames = True
        else:
            self.setMasterFilterFrequency(0)
            self.blackoutVideo()
            self.drawFrames = False
    def muteEffect(self, duration=None, beats=None):
        self.toggleAudioVisual(False)
        if duration is not None:
            self.timeline.cueInSeconds(duration, f=lambda: self.toggleAudioVisual(True))
        elif beats is not None:
            self.timeline.cueInBeats(beats, f=lambda: self.toggleAudioVisual(True))

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
    def bootup(self):
        def pingPongBootup(bootupVolume: float = Ableton.ZERO_DB):
            if bootupVolume < math.pow(0.75, AppWindow.BOOTUP_REPEATS) * Ableton.ZERO_DB:
                self.setPingPong(True)
                self.normalOperations()
                return
            self.ableton.getTrack('bootup').volume = bootupVolume
            self.bootupSound()
            self.executeOnUiThread(lambda: self.flicker(self.ableton.beatsToSeconds(4)))
            self.timeline.cueInBeats(4, f=lambda: pingPongBootup(bootupVolume * 0.75))
        self.setBeatRepeat(False)
        self.setPingPong(False)
        self.setFreeze(False)
        self.bootupSound()
        t = self.flickerEverything()
        self.timeline.cueInSeconds(t, lambda: pingPongBootup(Ableton.ZERO_DB))
        self.timeline.cueInSeconds(t, action=self.fadeFixture(self.spotlight, self.ableton.beatsToSeconds(4 * AppWindow.BOOTUP_REPEATS), 0, DmxLightboard.MAX_VALUE))

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
        self.timeline.cue(action=self.filterSweepMaster(sweepDuration, Ableton.MAX_FILTER_FREQUENCY, minFrequency))
        # fade out lights
        self.timeline.cue(action=self.fadeFixture(self.spotlight, sweepDuration, DmxLightboard.MAX_VALUE, 0))
        # flash a light
        self.timeline.cueInSeconds(flickerFixture, f=self.flickerFixture(self.spotlight, 0.5))
        # filter sweep master 0.5 * MAX to MAX
        self.timeline.cueInSeconds(reentry, action=self.filterSweepMaster(reentryDuration, minFrequency, Ableton.MAX_FILTER_FREQUENCY))
        # fade in lights
        self.timeline.cueInSeconds(reentry, action=self.fadeFixture(self.spotlight, reentryDuration, 0, DmxLightboard.MAX_VALUE))
        return reentry + reentryDuration

    def playPiano(self, clipNumber):
        piano = self.ableton.getTrack('grand piano')
        piano.play_clip(name=str(clipNumber))
    def shutdown(self):
        fadeVolumeToQuietDuration = 25
        fadeVolumeOutDuration = 5
        quiet = Ableton.ZERO_DB * 0.45
        self.playPiano(5)
        self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Office Space Printer'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Copywold'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Ambient Foley'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Beats'), fadeVolumeToQuietDuration, Ableton.ZERO_DB, quiet))
        self.timeline.cueInSeconds(fadeVolumeToQuietDuration, action=self.fadeVolume(self.ableton.getGroup('=Office Space Printer'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueInSeconds(fadeVolumeToQuietDuration, action=self.fadeVolume(self.ableton.getGroup('=Copywold'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueInSeconds(fadeVolumeToQuietDuration, action=self.fadeVolume(self.ableton.getGroup('=Ambient Foley'), fadeVolumeOutDuration, quiet, 0))
        self.timeline.cueInSeconds(fadeVolumeToQuietDuration, action=self.fadeVolume(self.ableton.getGroup('=Beats'), fadeVolumeOutDuration, quiet, 0))
    def normalOperations(self):
        self.executeOnUiThread(lambda: self.stream())
        self.timeline.cue(f=lambda: self.ableton.playClip('Modular UI'))
        self.timeline.cue(f=lambda: self.ableton.getTrack('slack').play_clip(name='3'))
        self.timeline.cue(f=lambda: self.ableton.playClip('machine belt 2'))
        self.timeline.cue(f=lambda: self.ableton.playClip('dreams tonite'))
        slackClipLength = 8 * 4
        self.timeline.cueInBeats(slackClipLength, f=lambda: self.ableton.getTrack('slack').play_clip(name='2'))
        self.timeline.cueInBeats(slackClipLength, f=lambda: self.ableton.playClip('808'))
        self.timeline.cueInBeats(2 * slackClipLength, f=lambda: self.ableton.getTrack('slack').play_clip(name='1'))
        random.seed()
        seconds = 15
        while seconds < 8 * AppWindow.ONE_MINUTE:
            self.timeline.cueInSeconds(seconds, f=lambda: self.flickerFixture(self.spotlight, 0.3))
            seconds += random.uniform(15, AppWindow.ONE_MINUTE)
        self.timeline.cueInSeconds(3 * AppWindow.ONE_MINUTE, f=self.playCopywold)
        self.timeline.cueInSeconds(6 * AppWindow.ONE_MINUTE, f=self.playOfficeSpacePrinter)
        self.timeline.cueInSeconds(8 * AppWindow.ONE_MINUTE, f=self.shutdown)
        self.timeline.cueInSeconds(AppWindow.SHOW_LENGTH_SECONDS, action=self.fadeFixture(self.spotlightClose, 5, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueInSeconds(AppWindow.SHOW_LENGTH_SECONDS, action=self.filterSweepMaster(1, Ableton.MAX_FILTER_FREQUENCY, Ableton.MIN_FILTER_FREQUENCY))
        self.timeline.cueInSeconds(AppWindow.SHOW_LENGTH_SECONDS, f=self.stopPerformance)

    def flickerEverything(self):
        end = 0
        for fixture in random.sample(self.par38 + self.par64, 11):
            end = max(end, self.flickerFixtureRandomly(fixture, random.randint(1, 15)))
        return end

    def playCopywold(self):
        def setBpm(bpm):
            self.ableton.setBpm(bpm)
            self.executeOnUiThread(lambda: self.frameTimer.start(self.ableton.millisecondsPerBeat(bpm)))
        def body():
            track = self.ableton.getTrack('test')
            # startVolume = Ableton.ZERO_DB * 0.5
            # track.volume = startVolume
            track.play_clip(name='tone')
            # self.timeline.cue(action=self.fadeVolume(track, 60, startVolume, Ableton.ZERO_DB))
            # self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Ambient Foley'), 60, Ableton.ZERO_DB, 0))
            bpm = [40, 80, 120, 160, 320, 320, 320, 320, 40]
            for i in range(len(bpm)):
                def _setBpm(bpm):
                    return lambda: setBpm(bpm)
                self.timeline.cueInBeats((i + 1) * 8, f=_setBpm(bpm[i]))
            self.timeline.cueInBeats(len(bpm) * 8, f=lambda: self.muteEffect(beats=8))
            self.timeline.cueInBeats(len(bpm) * 8 + 8, f=lambda: self.ableton.playClip('restart from crash'))
        def intro():
            self.executeOnUiThread(lambda: self.jitter(self.ableton.millisecondsPerBeat()))
            self.ableton.playClip('hihats L')
            self.ableton.playClip('hihats R')
            body()
        intro()

    def playOfficeSpacePrinter(self):
        def sweepAndFlicker():
            self.sweepEffect()
            self.flicker(4)
        def restartWavetable():
            self.ableton.playClip('Wavetable')
            self.flicker(4)
        self.executeOnUiThread(lambda: self.stream())
        self.ableton.setBpm(40)
        # self.ableton.getGroup('=Office Space Printer').volume = 0
        # self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Office Space Printer'), 120, 0, Ableton.ZERO_DB))
        # self.timeline.cue(action=self.fadeVolume(self.ableton.getGroup('=Copywold'), 90, Ableton.ZERO_DB, 0))
        self.ableton.playClip('Wavetable')
        self.ableton.playClip('Office Space Printer')
        self.timeline.cueInSeconds(30, f=sweepAndFlicker)
        self.timeline.cueInSeconds(60, f=restartWavetable)

    def playGrandPianoFinale(self):
        self.ableton.getTrack('grand piano').play_clip(name='5')

    def flickerOnFixture(self, fixture, flickerTimes):
        t = self.flickerFixtureRandomly(fixture, flickerTimes)
        self.timeline.cueInSeconds(t, f=lambda: fixture.fullOn())
        return t

    def fadeVolume(self, track: live.Track, durationSeconds: float, startLevel: float, endLevel: float):
        def updateFunction(value):
            track.volume = value
        return LerpAction(durationSeconds, updateFunction, startLevel, endLevel)

    def flickerFixtureRandomly(self, fixture, times=1):
        t = 0.0
        for i in range(times):
            random.seed()
            durationSeconds = random.uniform(AppWindow.FLICKER_DURATION[0], AppWindow.FLICKER_DURATION[1])
            self.timeline.cueInSeconds(t, f=lambda: self.flickerFixture(fixture, durationSeconds))
            delaySeconds = random.uniform(AppWindow.FLICKER_DELAY[0], AppWindow.FLICKER_DELAY[1])
            t += durationSeconds + delaySeconds
        return t

    def flickerFixture(self, fixture, durationSeconds):
        oldValues = fixture.values()
        self.timeline.cue(f=lambda: fixture.fractional(0.75))
        self.timeline.cueInSeconds(durationSeconds, f=lambda: fixture.set(oldValues))

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

    def test(self):
        def stopTest():
            self.stopVideo()
            self.blackoutVideo()
        testLength = 10
        self.ableton.stopAllClips()
        self.ableton.zeroAllTrackVolumes()
        self.ableton.play()
        officalTestTrack = self.ableton.getTrack('official test')
        officalTestTrack.play_clip(name='tone')
        self.timeline.cue(f=lambda: self.flickerFixtureRandomly(self.spotlightClose, times=5))
        self.timeline.cue(action=self.fadeVolume(officalTestTrack, 0, Ableton.ZERO_DB))
        self.timeline.cueInSeconds(testLength/2, action=self.fadeVolume(officalTestTrack, testLength/2, Ableton.ZERO_DB, 0))
        self.timeline.cue(action=self.fadeFixture(self.spotlight, testLength/2, 0, DmxLightboard.MAX_VALUE))
        self.timeline.cueInSeconds(testLength/2, action=self.fadeFixture(self.spotlight, testLength/2, DmxLightboard.MAX_VALUE, 0))
        self.timeline.cueInSeconds(testLength, f=stopTest)
        self.executeOnUiThread(lambda: self.stream())

    def stopVideo(self):
        if self.frameTimer is not None:
            self.frameTimer.stop()
            self.frameTimer = None

    def flicker(self, delaySeconds: float = 4):
        print('flickering {}'.format(delaySeconds))
        self.videoHeader.setDelaySeconds(delaySeconds)
        self.videoHeader.start()
        self.streamVideoHeader(self.videoHeader)

    def streamVideoHeader(self, videoHeader):
        def onTimeout():
            self.frame = videoHeader.getHead()
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoBuffer.get_max_fps())
        self.makeTimer(milliseconds, onTimeout)

    def stream(self):
        def onTimeout():
            self.frame = self.videoBuffer.get_last()
        milliseconds = MILLISECONDS_IN_SECOND / (self.videoBuffer.get_max_fps())
        self.makeTimer(milliseconds, onTimeout)

    def jitter(self, tickMilliseconds: float = 150.0):
        print(tickMilliseconds)
        def onTimeout():
            self.frame = self.videoBuffer.get_last()
        self.makeTimer(tickMilliseconds, onTimeout)

    def makeTimer(self, milliseconds, onTimeout):
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
        self.appState.quit()

    def resizeEvent(self, event):
        scaled_width = self.width()
        ratio = scaled_width / frame_width
        scaled_height = frame_height * ratio
        self.imageView.setFixedSize(QSize(scaled_width, scaled_height))

    def setCv2Frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 1)
        scaled_width = int(self.width())
        ratio = scaled_width / frame_width
        scaled_height = int(frame_height * ratio)
        frame = cv2.resize(frame, (scaled_width, scaled_height))
        qImage = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        self.imageView.setPixmap(QPixmap.fromImage(qImage))

    def blackoutVideo(self):
        self.imageView.clear()
