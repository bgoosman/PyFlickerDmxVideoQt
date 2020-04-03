from pyCreative.Action import *

class ActionFactory:
    def __init__(self, simulate):
        self.simulate = simulate

    def makeLerpAction(self, durationSeconds, updateFunction, start, end):
        if self.simulate:
            return InstantLerpAction(updateFunction, start, end)
        else:
            return LerpAction(durationSeconds, updateFunction, start, end)
