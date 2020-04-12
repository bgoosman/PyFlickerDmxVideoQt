import sys

from SoftwareEngineerPerformance import *

random.seed(10)
simulate = "--simulate" in sys.argv
performance = SoftwareEngineerPerformance(simulate)
