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

UI_FILENAME = "fullscreen_rawbuf1.ui"

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
        self.current_check_dict = {"ts0": True, "ts1": True, "peaks0": True, "peaks1": True}
        self.current_data_peaks_freq0_xplots = np.array([])
        self.current_data_peaks_freq1_xplots = np.array([])
        self.current_data_rawBuffer0_FFT = np.array([])
        self.current_data_rawBuffer1_FFT = np.array([])
        self.data_acqStamp_ucap = 0
        self.data_acqStamp = 1
        self.freeze_everything = False
        self.current_flags_dict = {"1,2":True, "5,6":True}

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.LoadDeviceFromTxt()

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf1")

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

        # pyqtgraph plot for rabuf1
        self.verticalLayout_Capture.removeItem(self.horizontalLayout)
        self.plot_rawbuf1 = pg.PlotWidget(title="rawBuf1")
        self.plot_rawbuf1.getPlotItem().enableAutoRange()
        self.plot_rawbuf1.getPlotItem().setAutoVisible()
        self.plot_rawbuf1.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf1.getPlotItem().showButtons()
        self.plot_rawbuf1.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf1.getPlotItem().setClipToView(True)
        self.plot_rawbuf1.setDownsampling(auto=True, mode="peak")
        self.plot_rawbuf1.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf1.getPlotItem().setLabel(axis='bottom', text='time (microseconds)')
        self.verticalLayout_Capture.addWidget(self.plot_rawbuf1)
        self.verticalLayout_Capture.addItem(self.horizontalLayout)

        # aggregator for Capture
        self.CValueAggregator_Capture = CValueAggregator(self)
        self.CValueAggregator_Capture.setProperty("inputChannels", ['{}/Capture'.format(self.current_device)])
        self.CValueAggregator_Capture.setObjectName("CValueAggregator_Capture")
        self.CValueAggregator_Capture.setValueTransformation("try:\n"
                                                             "    output(next(iter(values.values())))\n"
                                                             "except:\n"
                                                             "    output(0)")
        self.horizontalLayout_CValueAggregators.addWidget(self.CValueAggregator_Capture)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # checkbox for flags 1 and 2
        self.checkBox_bunch.stateChanged.connect(self.updateFlags_1_2)

        # checkbox for flags 5 and 6
        self.checkBox_turn.stateChanged.connect(self.updateFlags_5_6)

        # capture tab aggregator signals
        self.CValueAggregator_Capture.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCapture)

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCapture(self, data, verbose = False):

        # first time init
        self.firstTimeCapture = True

        # print
        if verbose:
            print("{} - Received data from the Capture property!".format(UI_FILENAME))

        # get acqStamp
        self.data_acqStamp = data['acqStamp']

        # print
        if verbose:
            print("{} - CAPTURE TIMESTAMP: {}".format(UI_FILENAME, self.data_acqStamp))

        # check that the arrays are different with respect to the previous iteration
        if self.bufferFirstPlotsPainted:
            if np.array_equal(self.data_rawBuf0, data['rawBuf0']) and np.array_equal(self.data_rawBuf1, data['rawBuf1']):
                return

        # freeze condition
        if not self.freeze_everything:

            # store the rest of the data
            self.data_rawBuf0 = data['rawBuf0']
            self.data_rawBuf1 = data['rawBuf1']
            self.data_rawBufFlags0 = data['rawBufFlags0']
            self.data_rawBufFlags1 = data['rawBufFlags1']
            self.data_acqStamp = data['acqStamp']
            self.data_cycleName = data['cycleName']

        # plot the data
        self.plotCaptureFunction()

        return

    #----------------------------------------------#

    # connect function
    def plotCaptureFunction(self, verbose = False):

        # get the time vector in microseconds only one time
        if self.compute_time_vector_first_time:
            Fs = 0.65
            self.time_vector = np.linspace(0, (len(self.data_rawBuf0) - 1) * (1 / (Fs * 1000)), num=len(self.data_rawBuf0))
            self.compute_time_vector_first_time = False

        # get only bunch flags (1 and 2) for buf1
        idx_flags_one_two = np.where((self.data_rawBufFlags1 == 1) | (self.data_rawBufFlags1 == 2))[0]
        flags_one_two = np.zeros(self.data_rawBufFlags1.shape)
        flags_one_two[idx_flags_one_two] = 1

        # get only turn flags (5 and 6) for buf1
        idx_flags_five_six = np.where((self.data_rawBufFlags1 == 5) | (self.data_rawBufFlags1 == 6))[0]
        flags_five_six = np.zeros(self.data_rawBufFlags1.shape)
        flags_five_six[idx_flags_five_six] = 1

        # line equation parameters
        offset_for_timestamps = 0
        y_1 = np.min(self.data_rawBuf1) - offset_for_timestamps
        y_2 = np.max(self.data_rawBuf1) + offset_for_timestamps
        x_1 = 0
        x_2 = 1
        self.data_turn_line_eq_params_1 = [float(x_1), float(x_2), float(y_1), float(y_2)]

        # re-scale the flags1 curve
        self.flags_bunch1 = ((self.data_turn_line_eq_params_1[3] - self.data_turn_line_eq_params_1[2]) /
                            self.data_turn_line_eq_params_1[1]) * flags_one_two + self.data_turn_line_eq_params_1[2]
        self.flags_turn1 = ((self.data_turn_line_eq_params_1[3] - self.data_turn_line_eq_params_1[2]) /
                            self.data_turn_line_eq_params_1[1]) * flags_five_six + self.data_turn_line_eq_params_1[2]

        # freeze condition
        if not self.freeze_everything:

            # plot the data for buf1
            self.plot_rawbuf1.getPlotItem().clear()
            if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
            if self.flags_turn1.size != 0 and self.is_turn1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

            # set cycle information
            self.CLabel_acqStamp_Capture.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
            self.CLabel_cycleName_Capture.setText("<b>cycleName:</b> {}".format(self.data_cycleName))

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

    # function for drawing flags 1 and 2
    def updateFlags_1_2(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf1.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Bunchs1 button checked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = True
            self.is_bunch1_checked = True
            self.plot_rawbuf1.getPlotItem().clear()
            if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
            if self.flags_turn1.size != 0 and self.is_turn1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

        else:

            # remove the flags
            print("{} - Bunchs1 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = False
            self.is_bunch1_checked = False
            self.plot_rawbuf1.getPlotItem().clear()
            if self.flags_turn1.size != 0 and self.is_turn1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf1.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function for drawing flags 5 and 6
    def updateFlags_5_6(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf1.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns1 button checked...".format(UI_FILENAME))
            self.current_flags_dict["5,6"] = True
            self.is_turn1_checked = True
            self.plot_rawbuf1.getPlotItem().clear()
            if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
            if self.flags_turn1.size != 0 and self.is_turn1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

        # if not
        else:

            # remove the flags
            print("{} - Turns1 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["5,6"] = False
            self.is_turn1_checked = False
            self.plot_rawbuf1.getPlotItem().clear()
            if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf1.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

########################################################
########################################################