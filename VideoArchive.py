import cv2
from pyCreative import *

class VideoArchive:
    def __init__(self, bufferSize=1, defaultFps=49):
        self.videos = []
        self.captures = []
        self.buffers = []
        self.headers = []
        self.bufferSize = bufferSize
        self.defaultFps = defaultFps
        self.index = 0
        self.playing = False

    def append(self, pathToVideo):
        self.videos.append(pathToVideo)

    def play(self):
        self.cleanup()
        for video in self.videos:
            capture = cv2.VideoCapture(video)
            self.captures.append(capture)
            fps = self.defaultFps if isinstance(video, str) else None
            buffer = VideoBuffer(capture, self.bufferSize, fps)
            self.buffers.append(buffer)
            header = VideoHeader(buffer)
            self.headers.append(header)
            buffer.start()
            header.start()
        self.playing = True

    def stop(self):
        for header in self.headers:
            header.stop()
        self.playing = False

    def cleanup(self):
        for buffer in self.buffers:
            buffer.cleanup()
            buffer.join()
        for capture in self.captures:
            capture.release()

    def setDelaySeconds(self, seconds):
        for header in self.headers:
            header.setDelaySeconds(seconds)

    def setIndex(self, index):
        self.index = index

    def next(self):
        self.index += 1
        if self.index == len(self.videos):
            self.index = 0
        return self.index

    def previous(self):
        self.index -= 1
        if self.index == -1:
            self.index = len(self.videos) - 1

    def getFrame(self, index=None):
        if index is None:
            index = self.index
        if index < len(self.headers):
            return self.headers[index].getLast()
        return None