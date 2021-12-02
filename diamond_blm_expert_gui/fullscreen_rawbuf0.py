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

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
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
        self.current_check_dict = {"ts0": True, "ts1": True, "peaks0": True, "peaks1": True}
        self.current_data_peaks_freq0_xplots = np.array([])
        self.current_data_peaks_freq1_xplots = np.array([])
        self.current_data_rawBuffer0_FFT = np.array([])
        self.current_data_rawBuffer1_FFT = np.array([])
        self.data_acqStamp_ucap = 0
        self.data_acqStamp = 1
        self.freeze_everything = False
        self.current_flags_dict = {"1,2":True, "5,6":True}
        self.data_save = {}
        self.is_buffer_plotted_in_the_main_window = "False"
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
        self.setWindowTitle("rawBuf0 - {}".format(self.current_device))

        # build code widgets
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()

        # handle signals and slots
        print("Handling signals and slots...")
        self.bindWidgets()

        # at this point comrad should be fully loaded
        self.is_comrad_fully_loaded = True

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # pyqtgraph plot for rabuf0
        self.verticalLayout_Capture.removeItem(self.horizontalLayout)
        self.plot_rawbuf0 = pg.PlotWidget(title="rawBuf0")
        self.plot_rawbuf0.getPlotItem().enableAutoRange()
        self.plot_rawbuf0.getPlotItem().setAutoVisible()
        # self.plot_rawbuf0.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0.getPlotItem().showButtons()
        self.plot_rawbuf0.getPlotItem().showGrid(x=True, y=True, alpha=0.3)
        self.plot_rawbuf0.getPlotItem().setClipToView(True)
        self.plot_rawbuf0.setDownsampling(auto=True, mode="peak")
        self.plot_rawbuf0.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf0.getPlotItem().setLabel(axis='bottom', text='time (microseconds)')
        self.verticalLayout_Capture.addWidget(self.plot_rawbuf0)
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

        # disable buttons until reception of data
        self.checkBox_bunch.setEnabled(False)
        self.checkBox_turn.setEnabled(False)

        # checkbox for sync signal
        self.checkBox_sync_main.stateChanged.connect(self.syncWithMainWindowFunction)
        self.checkBox_sync_main.hide()

        # capture tab aggregator signals
        self.CValueAggregator_Capture.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCapture)

        # init qtimer to check if the buffer is plotted in the main window
        self.timer_to_check_if_the_buffer_is_plotted_in_the_main_window = QTimer(self)
        self.timer_to_check_if_the_buffer_is_plotted_in_the_main_window.setInterval(250)
        self.timer_to_check_if_the_buffer_is_plotted_in_the_main_window.timeout.connect(self.readAuxBufferFileForFullscreen)
        self.timer_to_check_if_the_buffer_is_plotted_in_the_main_window.start()

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
                self.auxReceiveDataFromCapture(self.data_save)

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCapture(self, data, verbose = False):

        # save the received data
        self.data_save = data

        return

    #----------------------------------------------#

    # connect function
    def auxReceiveDataFromCapture(self, data, verbose = False):

        # check that the arrays are different with respect to the previous iteration
        if self.bufferFirstPlotsPainted:
            if np.array_equal(self.data_rawBuf0, data['rawBuf0']) and np.array_equal(self.data_rawBuf1, data['rawBuf1']):
                return

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

        # get only bunch flags (1 and 2) for buf0
        idx_flags_one_two = np.where((self.data_rawBufFlags0 == 1) | (self.data_rawBufFlags0 == 2))[0]
        flags_one_two = np.zeros(self.data_rawBufFlags0.shape)
        flags_one_two[idx_flags_one_two] = 1

        # get only turn flags (5 and 6) for buf0
        idx_flags_five_six = np.where((self.data_rawBufFlags0 == 5) | (self.data_rawBufFlags0 == 6))[0]
        flags_five_six = np.zeros(self.data_rawBufFlags0.shape)
        flags_five_six[idx_flags_five_six] = 1
        self.inf_lines_pos_0 = self.time_vector[idx_flags_five_six]

        # line equation parameters
        offset_for_timestamps = 0
        y_1 = np.min(self.data_rawBuf0) - offset_for_timestamps
        y_2 = np.max(self.data_rawBuf0) + offset_for_timestamps
        x_1 = 0
        x_2 = 1
        self.data_turn_line_eq_params_0 = [float(x_1), float(x_2), float(y_1), float(y_2)]

        # re-scale the flags0 curve
        self.flags_bunch0 = ((self.data_turn_line_eq_params_0[3] - self.data_turn_line_eq_params_0[2]) /
                            self.data_turn_line_eq_params_0[1]) * flags_one_two + self.data_turn_line_eq_params_0[2]
        self.flags_turn0 = ((self.data_turn_line_eq_params_0[3] - self.data_turn_line_eq_params_0[2]) /
                            self.data_turn_line_eq_params_0[1]) * flags_five_six + self.data_turn_line_eq_params_0[2]

        # freeze condition
        if not self.freeze_everything:

            # plot the data for buf0
            self.plot_rawbuf0.getPlotItem().clear()
            if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
            if self.flags_turn0.size != 0 and self.is_turn0_checked:
                # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                for line_pos in self.inf_lines_pos_0:
                    infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                    self.plot_rawbuf0.addItem(infinite_line)
            self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
            self.plot_rawbuf0.show()

            # set cycle information
            self.CLabel_acqStamp_Capture.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
            self.CLabel_cycleName_Capture.setText("<b>cycleName:</b> {}".format(self.data_cycleName))

        # update first plot boolean
        self.bufferFirstPlotsPainted = True

        # enable buttons
        self.checkBox_bunch.setEnabled(True)
        self.checkBox_turn.setEnabled(True)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxt(self):

        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt"), "r") as f:
                self.current_device = f.read()

        return

    #----------------------------------------------#

    # function for drawing flags 1 and 2
    def updateFlags_1_2(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf0.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Bunchs0 button checked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = True
            self.is_bunch0_checked = True
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        # if not
        else:

            # remove the flags
            print("{} - Bunchs0 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = False
            self.is_bunch0_checked = False
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf0.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function for drawing flags 5 and 6
    def updateFlags_5_6(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf0.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns0 button checked...".format(UI_FILENAME))
            self.current_flags_dict["5,6"] = True
            self.is_turn0_checked = True
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        else:

            # remove the flags
            print("{} - Turns0 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["5,6"] = False
            self.is_turn0_checked = False
            self.plot_rawbuf0.getPlotItem().clear()
            if self.bufferFirstPlotsPainted:
                if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf0.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # read aux txt
    def readAuxBufferFileForFullscreen(self):

        # if you want to sync the main with the fullscreen
        if self.sync_wrt_main:

            # read buffer boolean
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_0.txt")):
                with open(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_0.txt"), "r") as f:
                    self.is_buffer_plotted_in_the_main_window = f.read()

            # call plot function if buffer is plotted in the main window and we received the data
            if self.is_buffer_plotted_in_the_main_window == "True":

                # set the txt to false
                if self.bufferFirstPlotsPainted:
                    with open(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_0.txt"), "w") as f:
                        f.write("False")

                # call the plot function
                if self.data_save:
                    self.auxReceiveDataFromCapture(self.data_save)

        # if you do not want to sync the main with the fullscreen
        else:

            # call the plot function
            if self.data_save:
                self.auxReceiveDataFromCapture(self.data_save)

        return

    #----------------------------------------------#

    # function that does all operations that are required after comrad is fully loaded
    def doOperationsAfterComradIsFullyLoaded(self):

        # click the root and stop the timer when comrad is fully loaded
        if self.is_comrad_fully_loaded:

            # change the title of the app
            self.app.main_window.setWindowTitle("rawBuf0 - {}".format(self.current_device))

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