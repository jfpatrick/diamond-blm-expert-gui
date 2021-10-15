########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QBrush)
from PyQt5.QtCore import (QSize, Qt)
from PyQt5.QtWidgets import (QSizePolicy)
import connection_custom

# OTHER IMPORTS

import sys
import os

########################################################
########################################################

class MyDisplay(CDisplay):

    #----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):

        return 'main.ui'

    #----------------------------------------------#

    # init function
    def __init__(self, *args, **kwargs):

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.LoadDeviceFromTxtPremain()

        # other aux variables
        self.current_check_dict = {"ts0": True, "ts1": True, "peaks0": True, "peaks1": True}

        print("Loading main GUI file...")
        super().__init__(*args, **kwargs)
        self.setWindowTitle("BLM DIAMOND")
        """
        # init PyDM channels
        self.pydm_channel_capture_rawbuffer_0 = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
        self.pydm_channel_capture_rawbuffer_0_FFT = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0_FFT", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)
        self.pydm_channel_capture_rawbuffer_1 = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer1", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1)
        self.pydm_channel_capture_rawbuffer_1_FFT = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer1_FFT", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1_FFT)
        self.pydm_channel_capture_rawbuffer_0_timestamps = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#flags0_five_six", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
        self.pydm_channel_capture_rawbuffer_1_timestamps = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#flags1_five_six", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1)
        self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0_xplots", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)
        self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones = PyDMChannelDataSource(channel_address="rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1_xplots", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1_FFT)
        """
        print("Setting initial channels...")
        self.setChannels()

        print("Building the code-only widgets...")
        self.buildCodeWidgets()

        print("Handling signals and slots...")
        self.bindWidgets()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # change cursors of CRelatedDisplayButton to normal ArrowCursor
        self.CRelatedDisplayButton_rawBuf0.setCursor(QCursor(Qt.ArrowCursor))
        self.CRelatedDisplayButton_rawBuf0_FFT.setCursor(QCursor(Qt.ArrowCursor))
        self.CRelatedDisplayButton_rawBuf1.setCursor(QCursor(Qt.ArrowCursor))
        self.CRelatedDisplayButton_rawBuf1_FFT.setCursor(QCursor(Qt.ArrowCursor))

        # make push buttons invisible just to make the grid look nicer
        sp_retain0 = self.pushButton_invisible_0.sizePolicy()
        sp_retain0.setRetainSizeWhenHidden(True)
        self.pushButton_invisible_0.setSizePolicy(sp_retain0)
        self.pushButton_invisible_0.hide()
        sp_retain1 = self.pushButton_invisible_1.sizePolicy()
        sp_retain1.setRetainSizeWhenHidden(True)
        self.pushButton_invisible_1.setSizePolicy(sp_retain1)
        self.pushButton_invisible_1.hide()

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # checkbox for enabling and disabling turns of rawbuf0
        self.checkBox_turns_0.stateChanged.connect(self.pleaseShowTurns0)

        # checkbox for enabling and disabling turns of rawbuf1
        self.checkBox_turns_1.stateChanged.connect(self.pleaseShowTurns1)

        # checkbox for enabling and disabling peaks of rawbuf0_FFT
        self.checkBox_peaks_0.stateChanged.connect(self.pleaseShowPeaks0)

        # checkbox for enabling and disabling peaks of rawbuf1_FFT
        self.checkBox_peaks_1.stateChanged.connect(self.pleaseShowPeaks1)

        # write device into txt for fullscreen mode
        self.CRelatedDisplayButton_rawBuf0.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf1.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf0_FFT.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf1_FFT.clicked.connect(self.writeDeviceIntoTxtForFullScreen)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxtPremain(self):

        if os.path.exists("aux_txts/current_device_premain.txt"):
            with open("aux_txts/current_device_premain.txt", "r") as f:
                self.current_device = f.read()

        return

    #----------------------------------------------#

    # function that writes the device name into a txt file
    def writeDeviceIntoTxtForFullScreen(self):

        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        with open("aux_txts/current_device.txt", "w") as f:
            f.write(str(self.current_device))

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf0
    def pleaseShowTurns0(self, state):

        if state == Qt.Checked:

            print('turns0 button checked')
            self.current_check_dict["ts0"] = True
            self.CStaticPlot_Capture_rawBuf0.clear_items()
            self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            if self.current_check_dict["ts0"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0)
            self.pydm_channel_capture_rawbuffer_0.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

        else:

            print('turns0 button unchecked')
            self.current_check_dict["ts0"] = False
            self.CStaticPlot_Capture_rawBuf0.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            self.pydm_channel_capture_rawbuffer_0.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf1
    def pleaseShowTurns1(self, state):

        if state == Qt.Checked:

            print('turns1 button checked')
            self.current_check_dict["ts1"] = True
            self.CStaticPlot_Capture_rawBuf1.clear_items()
            self.CStaticPlot_Capture_rawBuf1.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps)
            if self.current_check_dict["ts1"]:
                self.CStaticPlot_Capture_rawBuf1.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1)
            self.pydm_channel_capture_rawbuffer_1.context_changed()
            self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

        else:

            print('turns1 button unchecked')
            self.current_check_dict["ts1"] = False
            self.CStaticPlot_Capture_rawBuf1.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps)
            self.pydm_channel_capture_rawbuffer_1.context_changed()
            self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf0_FFT
    def pleaseShowPeaks0(self, state):

        if state == Qt.Checked:

            print('peaks0 button checked')
            self.current_check_dict["peaks0"] = True
            self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
            self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT)
            if self.current_check_dict["peaks0"]:
                self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()


        else:

            print('peaks0 button unchecked')
            self.current_check_dict["peaks0"] = False
            self.CStaticPlot_Capture_rawBuf0_FFT.removeItem(
                self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf1_FFT
    def pleaseShowPeaks1(self, state):

        if state == Qt.Checked:

            print('peaks1 button checked')
            self.current_check_dict["peaks1"] = True
            self.CStaticPlot_Capture_rawBuf1_FFT.clear_items()
            self.CStaticPlot_Capture_rawBuf1_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT)
            if self.current_check_dict["peaks1"]:
                self.CStaticPlot_Capture_rawBuf1_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()


        else:

            print('peaks1 button unchecked')
            self.current_check_dict["peaks1"] = False
            self.CStaticPlot_Capture_rawBuf1_FFT.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()

        return

    #----------------------------------------------#

    # function that set the right channels for each widget depending on the selected device
    def setChannels(self):

        print("Setting channels for device {}".format(self.current_device))
        """
        # set channels for GeneralInformation tab
        self.CLabel_GeneralInformation_AcqStamp.channel = self.current_device + "/" + "GeneralInformation#acqStamp"
        self.CLabel_GeneralInformation_AutoGain.channel = self.current_device + "/" + "GeneralInformation#AutoGain"
        self.CLabel_GeneralInformation_BeamMomentum.channel = self.current_device + "/" + "GeneralInformation#BeamMomentum"
        self.CLabel_GeneralInformation_BoardId.channel = self.current_device + "/" + "GeneralInformation#BoardId"
        self.CLabel_GeneralInformation_BstShift.channel = self.current_device + "/" + "GeneralInformation#BstShift"
        self.CLabel_GeneralInformation_BunchSample.channel = self.current_device + "/" + "GeneralInformation#BunchSample"
        self.CLabel_GeneralInformation_FpgaCompilation.channel = self.current_device + "/" + "GeneralInformation#FpgaCompilation"
        self.CLabel_GeneralInformation_FpgaFirmware.channel = self.current_device + "/" + "GeneralInformation#FpgaFirmware"
        self.CLabel_GeneralInformation_FpgaStatus.channel = self.current_device + "/" + "GeneralInformation#FpgaStatus"
        self.CLabel_GeneralInformation_MachineId.channel = self.current_device + "/" + "GeneralInformation#MachineId"
        self.CLabel_GeneralInformation_MonitorNames.channel = self.current_device + "/" + "GeneralInformation#monitorNames"
        self.CLabel_GeneralInformation_TurnBc.channel = self.current_device + "/" + "GeneralInformation#TurnBc"
        self.CLabel_GeneralInformation_TurnDropped.channel = self.current_device + "/" + "GeneralInformation#TurnDropped"
        self.CLabel_GeneralInformation_TurnSample.channel = self.current_device + "/" + "GeneralInformation#TurnSample"

        # set channels for Capture tab rawBuffer0
        self.CContextFrame_CaptureTab_rawBuf0.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf0.selector = ""
        self.CStaticPlot_Capture_rawBuf0.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_timestamps, color=QColor("#F0E912"))
        self.CURVE_pydm_channel_capture_rawbuffer_0 = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source = self.pydm_channel_capture_rawbuffer_0, color=QColor("#FFFFFF"))
        self.pydm_channel_capture_rawbuffer_0.context_changed()
        self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

        # set channels for Capture tab rawBuffer1
        self.CContextFrame_CaptureTab_rawBuf1.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf1.selector = ""
        self.CStaticPlot_Capture_rawBuf1.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps = self.CStaticPlot_Capture_rawBuf1.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_timestamps, color=QColor("#F0E912"))
        self.CURVE_pydm_channel_capture_rawbuffer_1 = self.CStaticPlot_Capture_rawBuf1.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1, color=QColor("#FFFFFF"))
        self.pydm_channel_capture_rawbuffer_1.context_changed()
        self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

        # set channels for Capture tab rawBuffer0_FFT
        self.CContextFrame_CaptureTab_rawBuf0_FFT.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf0_FFT.selector = ""
        self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_0_FFT = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT, color=QColor("#FFFFFF"))
        self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones, color=QColor('yellow'), line_style=Qt.NoPen, symbol="o", symbol_size=8)
        self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
        self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        # set channels for Capture tab rawBuffer1_FFT
        self.CContextFrame_CaptureTab_rawBuf1_FFT.inheritSelector = False
        self.CContextFrame_CaptureTab_rawBuf1_FFT.selector = ""
        self.CStaticPlot_Capture_rawBuf1_FFT.clear_items()
        self.CURVE_pydm_channel_capture_rawbuffer_1_FFT = self.CStaticPlot_Capture_rawBuf1_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_FFT, color=QColor("#FFFFFF"))
        self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones = self.CStaticPlot_Capture_rawBuf1_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones, color=QColor('yellow'), line_style=Qt.NoPen, symbol="o", symbol_size=8)
        self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
        self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()

        # set channels for CLabel overtones of rawbuf0
        self.CContextFrame_CaptureTab_Overtones_FFT0.inheritSelector = False
        self.CContextFrame_CaptureTab_Overtones_FFT0.selector = ""
        self.CLabel_Overtones0_1.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_2.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_3.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_4.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_5.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_6.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
        self.CLabel_Overtones0_7.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"

        # set channels for CLabel overtones of rawbuf1
        self.CContextFrame_CaptureTab_Overtones_FFT1.inheritSelector = False
        self.CContextFrame_CaptureTab_Overtones_FFT1.selector = ""
        self.CLabel_Overtones1_1.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_2.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_3.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_4.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_5.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_6.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        self.CLabel_Overtones1_7.channel = "rda3://UCAP-NODE-BI-DIAMOND-BLM/UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
        """

        device = "dBLM.TEST4"
        """
        # set channels for AcqHistogram tab
        self.CLabel_AcqHistogramTab_BlmThr0.channel = device + "/" + "AcquisitionHistogram#blmthreshold0"
        self.CLabel_AcqHistogramTab_BlmThr1.channel = device + "/" + "AcquisitionHistogram#blmthreshold1"
        self.CLabel_AcqHistogramTab_Nsamples.channel = device + "/" + "AcquisitionHistogram#nsamples"
        self.CLabel_AcqHistogramTab_Nturns.channel = device + "/" + "AcquisitionHistogram#nturns"
        self.CContextFrame_AcqHistogramTab.inheritSelector = False
        self.CContextFrame_AcqHistogramTab.selector = ""
        self.CStaticPlot_AcqHistogramTab_blmBuf0.addCurve(data_source = device + "/" + "AcquisitionHistogram#blmbuf0")
        self.CStaticPlot_AcqHistogramTab_blmBuf1.addCurve(data_source = device + "/" + "AcquisitionHistogram#blmbuf1")
        """

        # set channels for AcqIntegral tab
        self.CLabel_AcqIntegralTab_BaselineSub.channel = device + "/" + "AcquisitionIntegral#baselineSub"
        self.CLabel_AcqIntegralTab_TurnAvgCnt.channel = device + "/" + "AcquisitionIntegral#turnAvgCnt"
        self.CLabel_AcqIntegralTab_ZeroSuppThr0.channel = device + "/" + "AcquisitionIntegral#zeroSuppThr0"
        self.CLabel_AcqIntegralTab_ZeroSuppThr1.channel = device + "/" + "AcquisitionIntegral#zeroSuppThr1"
        self.CLabel_AcqIntegralTab_ZeroSuppThrAve0.channel = device + "/" + "AcquisitionIntegral#zeroSuppThrAve0"
        self.CLabel_AcqIntegralTab_ZeroSuppThrAve1.channel = device + "/" + "AcquisitionIntegral#zeroSuppThrAve1"
        self.CContextFrame_AcqIntegralTab.inheritSelector = False
        self.CContextFrame_AcqIntegralTab.selector = ""
        self.CStaticPlot_AcqIntegralTab_intSumBuf0.addCurve(data_source = device + "/" + "AcquisitionIntegral#intSumBuf0")
        self.CStaticPlot_AcqIntegralTab_intSumBuf1.addCurve(data_source = device + "/" + "AcquisitionIntegral#intSumBuf1")

        # set channels for AcqIntegralDist tab
        self.CLabel_AcqIntegralDistTab_IntDistLsbCut0.channel = device + "/" + "AcquisitionIntegralDist#intDistLsbCut0"
        self.CLabel_AcqIntegralDistTab_IntDistLsbCut1.channel = device + "/" + "AcquisitionIntegralDist#intDistLsbCut1"
        self.CLabel_AcqIntegralDistTab_IntDistOffset0.channel = device + "/" + "AcquisitionIntegralDist#intDistOffset0"
        self.CLabel_AcqIntegralDistTab_IntDistOffset1.channel = device + "/" + "AcquisitionIntegralDist#intDistOffset1"
        self.CLabel_AcqIntegralDistTab_TurnAvgCnt.channel = device + "/" + "AcquisitionIntegralDist#turnAvgCnt"
        self.CContextFrame_AcqIntegralDistTab.inheritSelector = False
        self.CContextFrame_AcqIntegralDistTab.selector = ""
        self.CStaticPlot_AcqIntegralDistTab_intDistBuf0.addCurve(data_source = device + "/" + "AcquisitionIntegralDist#intDistBuf0")
        self.CStaticPlot_AcqIntegralDistTab_intDistBuf1.addCurve(data_source = device + "/" + "AcquisitionIntegralDist#intDistBuf1")

        # set channels for AcqRawDist tab
        self.CLabel_AcqRawDistTab_RawDistLsbCut0.channel = device + "/" + "AcquisitionRawDist#rawDistLsbCut0"
        self.CLabel_AcqRawDistTab_RawDistLsbCut1.channel = device + "/" + "AcquisitionRawDist#rawDistLsbCut1"
        self.CLabel_AcqRawDistTab_RawDistOffset0.channel = device + "/" + "AcquisitionRawDist#rawDistOffset0"
        self.CLabel_AcqRawDistTab_RawDistOffset1.channel = device + "/" + "AcquisitionRawDist#rawDistOffset1"
        self.CLabel_AcqRawDistTab_TurnAvgCnt.channel = device + "/" + "AcquisitionRawDist#turnAvgCnt"
        self.CContextFrame_AcqRawDistTab.inheritSelector = False
        self.CContextFrame_AcqRawDistTab.selector = ""
        self.CStaticPlot_AcqRawDistTab_rawDistBuf0.addCurve(data_source = device + "/" + "AcquisitionRawDist#rawDistBuf0")
        self.CStaticPlot_AcqRawDistTab_rawDistBuf1.addCurve(data_source = device + "/" + "AcquisitionRawDist#rawDistBuf1")

        # set channels for AcqTurnLoss tab
        self.CLabel_AcqTurnLossTab_BaselineSub.channel = device + "/" + "AcquisitionTurnLoss#baselineSub"
        self.CLabel_AcqTurnLossTab_TurnTrackCnt.channel = device + "/" + "AcquisitionTurnLoss#turnTrackCnt"
        self.CLabel_AcqTurnLossTab_ZeroSuppThr0.channel = device + "/" + "AcquisitionTurnLoss#zeroSuppThr0"
        self.CLabel_AcqTurnLossTab_ZeroSuppThr1.channel = device + "/" + "AcquisitionTurnLoss#zeroSuppThr1"
        self.CContextFrame_AcqTurnLossTab.inheritSelector = False
        self.CContextFrame_AcqTurnLossTab.selector = ""
        self.CStaticPlot_AcqTurnLossTab_turnLossBuf0.addCurve(data_source = device + "/" + "AcquisitionTurnLoss#turnLossBuf0")
        self.CStaticPlot_AcqTurnLossTab_turnLossBuf1.addCurve(data_source = device + "/" + "AcquisitionTurnLoss#turnLossBuf1")

        return

    #----------------------------------------------#

########################################################
########################################################