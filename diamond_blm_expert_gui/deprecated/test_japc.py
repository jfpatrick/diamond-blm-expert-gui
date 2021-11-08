import faulthandler
import sys
import os
import numpy as np
from copy import deepcopy
import jpype as jp
import time
import json
import math
import numpy as np
from time import sleep

import pyjapc

faulthandler.enable()

japc = pyjapc.PyJapc()
japc.setSelector("SPS.USER.ALL")

def myCallback(parameterName, newValue):
    print(f"New value for {parameterName} is: {newValue}")

japc.subscribeParam("SP.BA2.BLMDIAMOND.2/AcquisitionIntegral", myCallback)

japc.startSubscriptions()

while True:

    sleep(5)
