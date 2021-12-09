########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CValueAggregator, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData)
from PyQt5.QtGui import (QIcon, QColor)
from PyQt5.QtCore import (QSize, Qt, QTimer)
import pyqtgraph as pg

# OTHER IMPORTS

import sys
import os
import time
import numpy as np
import math
from general_utils import createCustomTempDir, getSystemTempDir

########################################################
########################################################

# GLOBALS

# ui file
UI_FILENAME = "fullscreen_rawbuf0_fft.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"

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

        # get temp dir
        self.app_temp_dir = os.path.join(getSystemTempDir(), TEMP_DIR_NAME)

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
        self.data_save = {}
        self.is_fft_plotted_in_the_main_window = "False"
        self.sync_wrt_main = True

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.LoadDeviceFromTxt()

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # aux variable for the after-fully-loaded-comrad operations
        self.is_comrad_fully_loaded = False

        # status bar message
        self.app.main_window.statusBar().showMessage("Successfully opened window for {}!".format(self.current_device), 30*1000)
        self.app.main_window.statusBar().repaint()

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf0_FFT - {}".format(self.current_device))

        # build code widgets
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()

        # handle signals and slots
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # at this point comrad should be fully loaded
        self.is_comrad_fully_loaded = True

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # pyqtgraph plot for rabuf0_fft
        self.verticalLayout_Capture_FFT.removeItem(self.horizontalLayout)
        self.plot_rawbuf0_fft = pg.PlotWidget(title="rawBuf0_FFT")
        self.plot_rawbuf0_fft.getPlotItem().enableAutoRange()
        self.plot_rawbuf0_fft.getPlotItem().setAutoVisible()
        # self.plot_rawbuf0_fft.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0_fft.getPlotItem().showButtons()
        self.plot_rawbuf0_fft.getPlotItem().showGrid(x=True, y=True, alpha=0.3)
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

        # disable buttons until reception of data
        self.checkBox_one.setEnabled(False)

        # checkbox for sync signal
        self.checkBox_sync_main.stateChanged.connect(self.syncWithMainWindowFunction)
        # self.checkBox_sync_main.hide()
        self.checkBox_sync_main.setToolTip("This checkbox synchronizes the FFT plots of the main and fullscreen panels so that the received data is plotted simultaneously in both windows."
                                           " It is usually required to compensate for the waiting times that UCAP imposes on the main window."
                                           " For example, if it is checked and the freezing option is enabled in the main window, none of the plots will be updated to new values."
                                           " When unchecked, data will be plotted as soon as it is received no matter what the current plot is shown in the main, which can be convenient when adjusting the phase of the signal or when using the TriggerCapture and ResetCapture commands.")

        # capture tab aggregator signals
        self.CValueAggregator_Capture_FFT.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCaptureFFT)

        # init qtimer to check if the fft is plotted in the main window
        self.timer_to_check_if_the_fft_is_plotted_in_the_main_window = QTimer(self)
        self.timer_to_check_if_the_fft_is_plotted_in_the_main_window.setInterval(250)
        self.timer_to_check_if_the_fft_is_plotted_in_the_main_window.timeout.connect(self.readAuxFFTFileForFullscreen)
        self.timer_to_check_if_the_fft_is_plotted_in_the_main_window.start()

        # set up a timer to HACK comrad after it is fully loaded
        self.timer_hack_operations_after_comrad_is_fully_loaded = QTimer(self)
        self.timer_hack_operations_after_comrad_is_fully_loaded.setInterval(1000)
        self.timer_hack_operations_after_comrad_is_fully_loaded.timeout.connect(self.doOperationsAfterComradIsFullyLoaded)
        self.timer_hack_operations_after_comrad_is_fully_loaded.start()

        return

    #----------------------------------------------#

    # function to handle sync wrt the main window
    def syncWithMainWindowFunction(self, state):

        # if the button is checked
        if state == Qt.Checked:

            # update boolean
            self.sync_wrt_main = True

        # if it is not checked
        else:

            # update boolean
            self.sync_wrt_main = False

            # call the plot function
            if self.data_save:
                self.auxReceiveDataFromCaptureFFT(self.data_save)

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCaptureFFT(self, data, verbose = False):

        # save the received data
        self.data_save = data

        return

    #----------------------------------------------#

    # connect function (aux)
    def auxReceiveDataFromCaptureFFT(self, data, verbose = False):

        # check data is different
        if self.firstTimeUcap:
            if np.array_equal(data['rawBuffer0_FFT'], self.data_rawBuffer0_FFT) and np.array_equal(data['rawBuffer1_FFT'], self.data_rawBuffer1_FFT):
                return

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

        # enable buttons
        self.checkBox_one.setEnabled(True)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxt(self):

        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt"), "r") as f:
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
            if self.bufferFirstPlotsPainted:
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
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0_fft.getPlotItem().clear()
                self.plot_rawbuf0_fft.plot(x=self.current_data_rawBuffer0_FFT[1, :], y=self.current_data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
                self.plot_rawbuf0_fft.show()

        return

    #----------------------------------------------#

    # read aux txt
    def readAuxFFTFileForFullscreen(self):

        # if you want to sync the main with the fullscreen
        if self.sync_wrt_main:

            # read fft boolean
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "is_fft_plotted_0.txt")):
                with open(os.path.join(self.app_temp_dir, "aux_txts", "is_fft_plotted_0.txt"), "r") as f:
                    self.is_fft_plotted_in_the_main_window = f.read()

            # call plot function if fft is plotted in the main window and we received the data
            if self.is_fft_plotted_in_the_main_window == "True":

                # set the txt to false
                if self.bufferFirstPlotsPainted:
                    with open(os.path.join(self.app_temp_dir, "aux_txts", "is_fft_plotted_0.txt"), "w") as f:
                        f.write("False")

                # call the plot function
                if self.data_save:
                    self.auxReceiveDataFromCaptureFFT(self.data_save)

        # if you do not want to sync the main with the fullscreen
        else:

            # call the plot function
            if self.data_save:
                self.auxReceiveDataFromCaptureFFT(self.data_save)

        return

    # ----------------------------------------------#

    # function that does all operations that are required after comrad is fully loaded
    def doOperationsAfterComradIsFullyLoaded(self):

        # click the root and stop the timer when comrad is fully loaded
        if self.is_comrad_fully_loaded:

            # change the title of the app
            self.app.main_window.setWindowTitle("rawBuf0_FFT - {}".format(self.current_device))

            # change the logo
            self.app.main_window.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))

            # hide the log console (not needed when using launcher.py)
            # self.app.main_window.hide_log_console()

            # finally stop the timer
            self.timer_hack_operations_after_comrad_is_fully_loaded.stop()

        return

    #----------------------------------------------#

########################################################
########################################################