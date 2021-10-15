########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData)
from PyQt5.QtGui import (QIcon, QColor)
from PyQt5.QtCore import (QSize, Qt)

# OTHER IMPORTS

import sys
import os
import time

########################################################
########################################################

# GLOBALS

UI_FILENAME = "fullscreen_rawbuf0.ui"

########################################################
########################################################

class MyDisplay(CDisplay):

    #----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):

        return UI_FILENAME

    #----------------------------------------------#

    # init function
    def __init__(self, *args, **kwargs):

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.LoadDeviceFromTxt()

        # other aux variables
        self.current_flags_dict = {"1,2":True, "5,6":True}

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf0")

        # init PyDM channels
        self.pydm_channel_capture_rawbuffer_0 = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
        self.pydm_channel_capture_rawbuffer_0_flags_1_2 = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#flags0_one_two", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
        self.pydm_channel_capture_rawbuffer_0_timestamps = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#flags0_five_six", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)

        # set the initial channels
        print("Setting initial channels...")
        self.setChannels()

        # handle signals and slots
        print("Handling signals and slots...")
        self.bindWidgets()

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # checkbox for flags 1 and 2
        self.checkBox_bunch.stateChanged.connect(self.updateFlags_1_2)

        # checkbox for flags 5 and 6
        self.checkBox_turn.stateChanged.connect(self.updateFlags_5_6)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxt(self):

        if os.path.exists("aux_txts/current_device.txt"):
            with open("aux_txts/current_device.txt", "r") as f:
                self.current_device = f.read()

        return

    #----------------------------------------------#

    # function for drawing flags 1 and 2
    def updateFlags_1_2(self, state):

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(False)

        if state == Qt.Checked:

            print('flags (1 and 2) button checked')
            self.current_flags_dict["1,2"] = True
            self.CStaticPlot_Capture_rawBuf0.clear_items()
            if self.current_flags_dict["1,2"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_flags_1_2)
            if self.current_flags_dict["5,6"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0)
            self.pydm_channel_capture_rawbuffer_0_flags_1_2.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()
            self.pydm_channel_capture_rawbuffer_0.context_changed()

        else:

            print('flags (1 and 2) button unchecked')
            self.current_flags_dict["1,2"] = False
            self.CStaticPlot_Capture_rawBuf0.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_0_flags_1_2)
            self.pydm_channel_capture_rawbuffer_0_flags_1_2.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()
            self.pydm_channel_capture_rawbuffer_0.context_changed()

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function for drawing flags 5 and 6
    def updateFlags_5_6(self, state):

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(False)

        if state == Qt.Checked:

            print('flags (5 and 6) button checked')
            self.current_flags_dict["5,6"] = True
            self.CStaticPlot_Capture_rawBuf0.clear_items()
            if self.current_flags_dict["1,2"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_flags_1_2)
            if self.current_flags_dict["5,6"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0)
            self.pydm_channel_capture_rawbuffer_0_flags_1_2.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()
            self.pydm_channel_capture_rawbuffer_0.context_changed()

        else:

            print('flags (5 and 6) button unchecked')
            self.current_flags_dict["5,6"] = False
            self.CStaticPlot_Capture_rawBuf0.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            self.pydm_channel_capture_rawbuffer_0_flags_1_2.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()
            self.pydm_channel_capture_rawbuffer_0.context_changed()

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function that set the right channels for each widget depending on the selected device
    def setChannels(self):

        # set channels for Capture tab rawBuffer0
        self.CContextFrame_CaptureTab_rawBuf0.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf0.selector = ""
        self.CStaticPlot_Capture_rawBuf0.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_0_flags_1_2 = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_flags_1_2, color=QColor("#EF476F"))
        self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_timestamps, color=QColor("#F0E912"))
        self.CURVE_pydm_channel_capture_rawbuffer_0 = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0, color=QColor("#FFFFFF"))
        self.CStaticPlot_Capture_rawBuf0.setDownsampling(auto=True, mode="peak")
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(True)
        self.pydm_channel_capture_rawbuffer_0_flags_1_2.context_changed()
        self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()
        self.pydm_channel_capture_rawbuffer_0.context_changed()

        # let's uncheck flags1 and flags2 at the beginning
        self.checkBox_bunch.setChecked(False)
        self.updateFlags_1_2(False)

        return

########################################################
########################################################