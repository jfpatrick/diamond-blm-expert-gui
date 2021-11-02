########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CValueAggregator, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData)
from PyQt5.QtGui import (QIcon, QColor)
from PyQt5.QtCore import (QSize, Qt)
import pyqtgraph as pg

# OTHER IMPORTS

import sys
import os
import time
import numpy as np
import math

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

        # init aux booleans and variables
        self.data_aux_time = math.inf
        self.bufferFirstPlotsPainted = False
        self.compute_time_vector_first_time = True
        self.firstTimeUcap = False
        self.firstTimeCapture = False
        self.data_rawBuf0 = np.array([0])
        self.data_rawBuf1 = np.array([0])
        self.is_turn0_checked = True
        self.is_turn1_checked = True
        self.is_bunch0_checked = False
        self.is_bunch1_checked = False
        self.is_peaks0_checked = True
        self.is_peaks1_checked = True
        self.current_check_dict = {"peaks": True}
        self.current_data_peaks_freq0_xplots = np.array([])
        self.current_data_peaks_freq1_xplots = np.array([])
        self.current_data_rawBuffer0_FFT = np.array([])
        self.current_data_rawBuffer1_FFT = np.array([])
        self.data_acqStamp_ucap = 0
        self.data_acqStamp = 1
        self.freeze_everything = False

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.LoadDeviceFromTxt()

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf0_FFT")

        # build code widgets
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()

        # handle signals and slots
        print("Handling signals and slots...")
        self.bindWidgets()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # pyqtgraph plot for rabuf0_fft
        self.verticalLayout_Capture_FFT.removeItem(self.horizontalLayout)
        self.plot_rawbuf0_fft = pg.PlotWidget(title="rawBuf0_FFT")
        self.plot_rawbuf0_fft.getPlotItem().enableAutoRange()
        self.plot_rawbuf0_fft.getPlotItem().setAutoVisible()
        self.plot_rawbuf0_fft.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0_fft.getPlotItem().showButtons()
        self.plot_rawbuf0_fft.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf0_fft.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf0_fft.getPlotItem().setLabel(axis='bottom', text='frequency (kHz)')
        self.verticalLayout_Capture_FFT.addWidget(self.plot_rawbuf0_fft)
        self.verticalLayout_Capture_FFT.addItem(self.horizontalLayout)

        # aggregator for Capture FFT (UCAP)
        self.CValueAggregator_Capture_FFT = CValueAggregator(self)
        self.CValueAggregator_Capture_FFT.setProperty("inputChannels", ['UCAP.VD.{}/bufferFFT'.format(self.current_device)])
        self.CValueAggregator_Capture_FFT.setObjectName("CValueAggregator_Capture_FFT")
        self.CValueAggregator_Capture_FFT.setValueTransformation("try:\n"
                                                             "    output(next(iter(values.values())))\n"
                                                             "except:\n"
                                                             "    output(0)")
        self.horizontalLayout_CValueAggregators.addWidget(self.CValueAggregator_Capture_FFT)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # checkbox for peaks signal
        self.checkBox_one.stateChanged.connect(self.updatePeaks)

        # capture tab aggregator signals
        self.CValueAggregator_Capture_FFT.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCaptureFFT)

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCaptureFFT(self, data, verbose = False):

        # first time init
        self.firstTimeUcap = True

        # print
        if verbose:
            print("{} - Received data from the UCAP node!".format(UI_FILENAME))

        # freeze condition
        if not self.freeze_everything:

            # store the data
            self.data_aux_time = data['aux_time']
            self.data_rawBuffer0_FFT = data['rawBuffer0_FFT']
            self.data_rawBuffer1_FFT = data['rawBuffer1_FFT']
            self.data_peaks_freq0 = data['peaks_freq0']
            self.data_peaks_freq1 = data['peaks_freq1']
            self.data_peaks_freq0_xplots = data['peaks_freq0_xplots']
            self.data_peaks_freq1_xplots = data['peaks_freq1_xplots']
            self.data_turn_line_eq_params_0 = data['turn_line_eq_params_0']
            self.data_turn_line_eq_params_1 = data['turn_line_eq_params_1']
            self.data_acqStamp_ucap = data['acqStamp']
            self.data_cycleName_ucap = data['cycleName']

        # print
        if verbose:
            print("{} - UCAP TIMESTAMP: {}".format(UI_FILENAME, self.data_acqStamp_ucap))

        # plot the data
        self.plotCaptureFFTFunction()

        return

    #----------------------------------------------#

    # connect function
    def plotCaptureFFTFunction(self, verbose = False):

        # save current buffer ffts for checkbuttons
        self.current_data_peaks_freq0_xplots = self.data_peaks_freq0_xplots
        self.current_data_peaks_freq1_xplots = self.data_peaks_freq1_xplots
        self.current_data_rawBuffer0_FFT = self.data_rawBuffer0_FFT
        self.current_data_rawBuffer1_FFT = self.data_rawBuffer1_FFT

        # freeze condition
        if not self.freeze_everything:

            # plot the data for buf0_fft
            self.plot_rawbuf0_fft.getPlotItem().clear()
            if self.data_peaks_freq0_xplots.size != 0 and self.is_peaks0_checked:
                self.plot_rawbuf0_fft.plot(x=self.data_peaks_freq0_xplots[1], y=self.data_peaks_freq0_xplots[0], pen=None, symbolBrush=(255, 255, 0), symbol='x', symbolPen=(255, 255, 0), symbolSize=8, name="rawBuf0_peaks")
            self.plot_rawbuf0_fft.plot(x=self.data_rawBuffer0_FFT[1, :], y=self.data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
            self.plot_rawbuf0_fft.show()

            # set cycle information
            self.CLabel_acqStamp_Capture.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp_ucap))
            self.CLabel_cycleName_Capture.setText("<b>cycleName:</b> {}".format(self.data_cycleName_ucap))

        # update first plot boolean
        self.bufferFirstPlotsPainted = True

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

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Peaks0 button checked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = True
            self.is_peaks0_checked = True
            self.plot_rawbuf0_fft.getPlotItem().clear()
            if self.data_peaks_freq0_xplots.size != 0:
                self.plot_rawbuf0_fft.plot(x=self.current_data_peaks_freq0_xplots[1], y=self.current_data_peaks_freq0_xplots[0], pen=None, symbolBrush=(255, 255, 0), symbol='x', symbolPen=(255, 255, 0), symbolSize=8, name="rawBuf0_peaks")
            if self.current_check_dict["peaks0"]:
                self.plot_rawbuf0_fft.plot(x=self.current_data_rawBuffer0_FFT[1, :], y=self.current_data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
            self.plot_rawbuf0_fft.show()

        # if not
        else:

            # remove the peaks
            print("{} - Peaks0 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = False
            self.is_peaks0_checked = False
            self.plot_rawbuf0_fft.getPlotItem().clear()
            self.plot_rawbuf0_fft.plot(x=self.current_data_rawBuffer0_FFT[1, :], y=self.current_data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
            self.plot_rawbuf0_fft.show()

        return

    #----------------------------------------------#

########################################################
########################################################