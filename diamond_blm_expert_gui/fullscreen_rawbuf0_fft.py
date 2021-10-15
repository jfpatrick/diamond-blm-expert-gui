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

UI_FILENAME = "fullscreen_rawbuf0_fft.ui"

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
        self.current_check_dict = {"peaks":True}

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf0_FFT")

        # init PyDM channels
        self.pydm_channel_capture_rawbuffer_0_FFT = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0_FFT", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)
        self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0_xplots", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)

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

        # checkbox for peaks signal
        self.checkBox_one.stateChanged.connect(self.updatePeaks)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxt(self):

        if os.path.exists("aux_txts/current_device.txt"):
            with open("aux_txts/current_device.txt", "r") as f:
                self.current_device = f.read()

        return

    #----------------------------------------------#

    # function for drawing the fft peaks
    def updatePeaks(self, state):

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(False)

        if state == Qt.Checked:

            print('peaks button checked')
            self.current_check_dict["peaks"] = True
            self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
            self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT)
            if self.current_check_dict["peaks"]:
                self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()


        else:

            print('peaks button unchecked')
            self.current_check_dict["peaks"] = False
            self.CStaticPlot_Capture_rawBuf0_FFT.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function that set the right channels for each widget depending on the selected device
    def setChannels(self):

        # set channels for Capture tab rawBuffer0_FFT
        self.CContextFrame_CaptureTab_rawBuf0_FFT.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf0_FFT.selector = ""
        self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_0_FFT = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT, color=QColor("#FFFFFF"))
        self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones, color=QColor("yellow"), line_style=Qt.NoPen, symbol="o")
        self.CStaticPlot_Capture_rawBuf0_FFT.setDownsampling(auto=True, mode="peak")
        # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(True)
        self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
        self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        return

########################################################
########################################################