########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QAbstractTableModel, QEventLoop, QCoreApplication, QTimer)
from PyQt5.QtWidgets import (QTableView, QSizePolicy, QAbstractItemView, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget, QProgressDialog)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import numpy as np
from general_utils import createCustomTempDir, getSystemTempDir
import jpype as jp
import json
from datetime import datetime, timedelta, timezone
from copy import deepcopy

########################################################
########################################################

# GLOBALS

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
UI_FILENAME = "preview_summary.ui"
ACCEPTANCE_FACTOR = 2.00
TURN_TIME_LHC = 89.0000 # microseconds
TURN_TIME_SPS = 23.0543 # microseconds

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels_horizontal, header_labels_vertical, error_dict={}):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels_horizontal = header_labels_horizontal
        self._header_labels_vertical = header_labels_vertical
        self.error_dict = error_dict

        return

    def headerData(self, section, orientation, role):

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and self._header_labels_horizontal:
                return self._header_labels_horizontal[section]
            elif orientation == Qt.Vertical and self._header_labels_vertical:
                return self._header_labels_vertical[section]

    def data(self, index, role):

        row = index.row()
        col = index.column()

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif role == Qt.DisplayRole:
            value = self._data[row][col]
            return value
        elif role == Qt.ToolTipRole and self.error_dict[row][col] != "" and self._data[row][col] != "-":
            return self.error_dict[row][col]
        elif role == Qt.ForegroundRole and self.error_dict[row][col] != "":
            if self._data[row][col] == "-" and self.error_dict[row][col] == "NOT_WORKING_DEVICE":
                return QBrush(QColor("red"))
            else:
                return QBrush(QColor("#FF6C00"))
        elif role == Qt.BackgroundRole and self.error_dict[row][col] != "":
            if self._data[row][col] == "-":
                return QBrush(QColor("#FFE2E2"))
            else:
                return QBrush(QColor("#F8F0DD"))

    def rowCount(self, index):

        return len(self._data)

    def columnCount(self, index):

        return len(self._data[0])

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

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # import cern package for handling exceptions
        self.cern = jp.JPackage("cern")

        # retrieve the pyccda json info file
        self.readPyCCDAJsonFile()

        # set the device list
        self.device_list = ["SP.BA1.BLMDIAMOND.2", "SP.BA2.BLMDIAMOND.2", "SP.BA4.BLMDIAMOND.2", "SP.BA6.BLMDIAMOND.2", "dBLM.TEST4"]
        self.LoadDeviceListFromTxtPremain()

        # order the device list
        self.device_list.sort()

        # input the property list
        self.field_list = ["BeamMomentum", "BstShift", "BunchSample", "FpgaCompilation", "FpgaFirmware", "FpgaStatus", "TurnBc", "TurnDropped", "TurnSample"]

        # order the property list
        self.field_list.sort()

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.device_list[0]]["acquisition"].keys())

        # order the property list
        self.property_list.sort()

        # create japc object
        # self.japc = pyjapc.PyJapc(incaAcceleratorName = None) # use this line when launching the main application
        self.japc = pyjapc.PyJapc() # use this line when launching the module for debugging

        # set japc selector
        self.japc.setSelector("")

        # load the gui, build the widgets and handle the signals
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("BLM DIAMOND SETTINGS")
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # status bar message
        self.app.main_window.statusBar().showMessage("Device summary of {} loaded!".format(self.current_accelerator), 10*1000)
        self.app.main_window.statusBar().repaint()

        # close progress bar
        self.progress_dialog.close()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # init progress bar
        self.progress_dialog = QProgressDialog("Opening summary view for {} devices...".format(self.current_accelerator), None, 0, (len(self.property_list)-1)*len(self.device_list))
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setWindowTitle("Progress")
        self.progress_dialog.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        self.progress_dialog.repaint()
        self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

        # create gui using pyuic5
        self.tableView_summary = QTableView(self.frame_summary)
        self.tableView_summary.setStyleSheet("QTableView{\n"
                                                         "    background-color: rgb(243, 243, 243);\n"
                                                         "}")
        self.tableView_summary.setFrameShape(QFrame.StyledPanel)
        self.tableView_summary.setFrameShadow(QFrame.Plain)
        self.tableView_summary.setDragEnabled(False)
        self.tableView_summary.setAlternatingRowColors(True)
        self.tableView_summary.setSelectionMode(QAbstractItemView.NoSelection)
        self.tableView_summary.setShowGrid(True)
        self.tableView_summary.setGridStyle(Qt.SolidLine)
        self.tableView_summary.setObjectName("tableView_summary")
        self.tableView_summary.horizontalHeader().setHighlightSections(False)
        self.tableView_summary.horizontalHeader().setMinimumSectionSize(50)
        self.tableView_summary.horizontalHeader().setStretchLastSection(True)
        self.tableView_summary.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.tableView_summary.verticalHeader().setVisible(False)
        self.tableView_summary.verticalHeader().setDefaultSectionSize(25)
        self.tableView_summary.verticalHeader().setHighlightSections(False)
        self.tableView_summary.verticalHeader().setMinimumSectionSize(25)
        self.tableView_summary.verticalHeader().setStretchLastSection(True)
        self.tableView_summary.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.verticalLayout_frame_summary.addWidget(self.tableView_summary)

        # init model data list of lists
        self.summary_data = []
        self.error_dict = {}

        # counter for the dialog progress bar
        dialog_counter = 0

        # iterate over fields and properties
        for r in range(0, len(self.field_list)+len(self.property_list)):

            # init row list
            row_list = []

            # init error dict for that row
            self.error_dict[r] = {}

            # operate as a field
            if r < len(self.field_list):

                # declare the field
                field = self.field_list[r]

                # append first element which is the field / mode
                row_list.append(str(field))
                self.error_dict[r][0] = ""

                # iterate over devices
                for c, device in enumerate(self.device_list):

                    # if the device IS working
                    if device in self.working_devices:

                        # selectorOverride for GeneralInformation should be empty
                        selectorOverride = ""

                        # get field values via pyjapc
                        try:
                            field_value = self.japc.getParam("{}/{}#{}".format(device, "GeneralInformation", field), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)
                            row_list.append(str(field_value))
                            self.error_dict[r][c+1] = ""
                        except:
                            pass

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        self.error_dict[r][c+1] = "NOT_WORKING_DEVICE"

            # operate as a mode
            else:

                # declare the property
                property = self.property_list[r-len(self.field_list)]

                # skip general information property
                if property == "GeneralInformation":
                    continue

                # append first element which is the field / mode
                row_list.append(str(property))
                self.error_dict[r][0] = ""

                # iterate over devices
                for c, device in enumerate(self.device_list):

                    # update progress bar
                    self.progress_dialog.setValue(dialog_counter)
                    self.progress_dialog.repaint()
                    self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

                    # if the device IS working
                    if device in self.working_devices:

                        # selectorOverride for the working modules table has to be a specific selector
                        # use an empty selector for LHC devices
                        if self.current_accelerator == "LHC":
                            selectorOverride = ""
                        # use SPS.USER.ALL for SPS devices
                        elif self.current_accelerator == "SPS":
                            selectorOverride = "SPS.USER.SFTPRO1"
                        # use an empty selector for the others
                        else:
                            selectorOverride = ""

                        # get nturns
                        try:

                            # in the LHC: 1 turn = 89 microseconds (updates each 1 second if nturn = 11245)
                            # in the SPS: 1 turn = 23.0543 microseconds (updates each 0.1 second if nturn = 4338)
                            if property == "AcquisitionHistogram":
                                is_multiplexed = self.pyccda_dictionary[self.current_accelerator][device]["setting"]["BeamLossHistogramSetting"]["mux"]
                                if is_multiplexed == "False":
                                    selectorOverride = ""
                                nturns = float(self.japc.getParam("{}/{}#{}".format(device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                            elif property == "AcquisitionIntegral" or property == "AcquisitionIntegralDist" or property == "AcquisitionRawDist":
                                is_multiplexed = self.pyccda_dictionary[self.current_accelerator][device]["setting"]["BeamLossIntegralSetting"]["mux"]
                                if is_multiplexed == "False":
                                    selectorOverride = ""
                                nturns = float(self.japc.getParam("{}/{}#{}".format(device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                            elif property == "AcquisitionTurnLoss":
                                is_multiplexed = self.pyccda_dictionary[self.current_accelerator][device]["setting"]["TurnLossMeasurementSetting"]["mux"]
                                if is_multiplexed == "False":
                                    selectorOverride = ""
                                nturns = float(self.japc.getParam("{}/{}#{}".format(device, "TurnLossMeasurementSetting", "turnTrackCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                            elif property == "Capture":
                                pass
                            else:
                                print("{} - Error (unknown property {})".format(UI_FILENAME, property))
                            if self.current_accelerator == "LHC":
                                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
                            elif self.current_accelerator == "SPS":
                                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
                            else:
                                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000

                        # if this does not work, then nothing should be working (NO_DATA_AVAILABLE_FOR_USER likely)
                        except Exception as xcp:

                            # pass and print exception
                            print(xcp)
                            pass

                        # selectorOverride for the working modules table has to be a specific selector
                        # use an empty selector for LHC devices
                        if self.current_accelerator == "LHC":
                            selectorOverride = ""
                        # use SPS.USER.ALL for SPS devices
                        elif self.current_accelerator == "SPS":
                            selectorOverride = "SPS.USER.SFTPRO1"
                        # use an empty selector for the others
                        else:
                            selectorOverride = ""

                        # do a GET request via japc
                        try:

                            # get the fields
                            field_values = self.japc.getParam("{}/{}".format(device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)

                            # get timestamps
                            get_ts = field_values[1]["acqStamp"]
                            current_ts = datetime.now(timezone.utc)

                            # for the capture do not care about timestamps
                            if property == "Capture":

                                # if the buffer is not empty
                                if field_values[0]["rawBuf0"].size > 0:

                                    # if the try did not give an error then it is working
                                    row_list.append(str(field_values[1]["acqStamp"]))
                                    self.error_dict[r][c + 1] = ""

                                # if buffers are empty show a custom error
                                else:

                                    # BUFFERS_ARE_EMPTY
                                    row_list.append("BUFFERS_ARE_EMPTY")
                                    self.error_dict[r][c + 1] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

                            # for the others we should care about timestamps
                            else:

                                # show a custom error if nturns is 0
                                if nturns == 0:

                                    # NTURNS_IS_ZERO
                                    row_list.append("NTURNS_IS_ZERO")
                                    self.error_dict[r][c + 1] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

                                # normal procedure
                                else:

                                    # compare timestamps
                                    if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):
                                        row_list.append("MODE_BEING_ANALYZED")
                                        self.error_dict[r][c + 1] = "custom.message.error: MODE_BEING_ANALYZED: The mode {} is still being analyzed in a different thread. Wait a few seconds until a decision about its availability is made.".format(property)
                                    else:
                                        row_list.append("TS_TOO_OLD")
                                        self.error_dict[r][c + 1] = "custom.message.error: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

                        # this exception is usually NO_DATA_AVAILABLE_FOR_USER (happens when it is not initialized yet)
                        except self.cern.japc.core.ParameterException as xcp:

                            # NO_DATA_AVAILABLE_FOR_USER
                            row_list.append(str(xcp.getMessage()).split(":")[0])
                            self.error_dict[r][c + 1] = str(xcp)

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        self.error_dict[r][c + 1] = "NOT_WORKING_DEVICE"

                    # update dialog counter
                    dialog_counter += 1

            # append the row to the full summary data
            self.summary_data.append(row_list)

        # set the header names
        self.summary_header_labels_horizontal = ["Field / Mode"] + self.device_list

        # summary model
        self.model_summary = TableModel(data=self.summary_data, header_labels_horizontal=self.summary_header_labels_horizontal, header_labels_vertical=[], error_dict=self.error_dict)
        self.tableView_summary.setModel(self.model_summary)
        self.tableView_summary.update()
        self.tableView_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for c in range(0, len(self.summary_header_labels_horizontal)):
            self.tableView_summary.setColumnWidth(c, 200)
        self.tableView_summary.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView_summary.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView_summary.setFocusPolicy(Qt.NoFocus)
        self.tableView_summary.setSelectionMode(QAbstractItemView.NoSelection)
        self.tableView_summary.horizontalHeader().setFixedHeight(30)
        self.tableView_summary.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.tableView_summary.verticalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.tableView_summary.show()

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # nothing to do here
        pass

        # set up a timer to load the QThread premain updates
        self.timer_load_txt_with_qthread_premain_updates = QTimer(self)
        self.timer_load_txt_with_qthread_premain_updates.setInterval(1000)
        self.timer_load_txt_with_qthread_premain_updates.timeout.connect(self.updateWorkingModes)
        self.timer_load_txt_with_qthread_premain_updates.start()

        return

    #----------------------------------------------#

    # function that updates the working modes
    def updateWorkingModes(self):

        # init new variables
        error_dict_new = {}
        summary_data_new = []

        # iterate over fields and properties
        for r in range(0, len(self.field_list) + len(self.property_list)):

            # init row list
            row_list = []

            # init error dict for that row
            error_dict_new[r] = {}

            # operate as a field
            if r < len(self.field_list):

                # declare the field
                field = self.field_list[r]

                # append first element which is the field / mode
                row_list.append(str(field))
                error_dict_new[r][0] = ""

                # iterate over devices
                for c, device in enumerate(self.device_list):

                    # if the device IS working
                    if device in self.working_devices:

                        # copy existing table fields
                        field_value = self.summary_data[r][c+1]
                        row_list.append(str(field_value))
                        error_dict_new[r][c+1] = self.error_dict[r][c+1]

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        error_dict_new[r][c+1] = "NOT_WORKING_DEVICE"

            # operate as a mode
            else:

                # declare the property
                property = self.property_list[r - len(self.field_list)]

                # skip general information property
                if property == "GeneralInformation":
                    continue

                # append first element which is the field / mode
                row_list.append(str(property))
                error_dict_new[r][0] = ""

                # iterate over devices
                for c, device in enumerate(self.device_list):

                    # if the device IS working
                    if device in self.working_devices:

                        # check dirs exist
                        if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_{}.json".format(device))) and os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_{}.json".format(device))):

                            # load the new data
                            with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_{}.json".format(device))) as f:
                                modules_data_new = json.load(f)
                            with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_{}.json".format(device))) as f:
                                errors_new = json.load(f)

                            # update with new json values
                            if property in modules_data_new.keys():
                                row_list.append(modules_data_new[property])
                                error_dict_new[r][c+1] = errors_new[property]
                            else:
                                row_list.append(self.summary_data[r][c+1])
                                error_dict_new[r][c+1] = self.error_dict[r][c+1]

                        # dont get value from json (get it from previous table)
                        else:

                            # copy existing table values
                            row_list.append(self.summary_data[r][c+1])
                            error_dict_new[r][c+1] = self.error_dict[r][c+1]

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        error_dict_new[r][c+1] = "NOT_WORKING_DEVICE"

            # append the row to the full summary data
            summary_data_new.append(row_list)

        # if nothing changed just skip
        if self.summary_data == summary_data_new:
            return

        # update variables
        self.summary_data = deepcopy(summary_data_new)
        self.error_dict = deepcopy(error_dict_new)
        del summary_data_new
        del error_dict_new

        # update table
        self.model_summary = TableModel(data=self.summary_data, header_labels_horizontal=self.summary_header_labels_horizontal, header_labels_vertical=[], error_dict=self.error_dict)
        self.tableView_summary.setModel(self.model_summary)
        self.tableView_summary.update()

        return

    #----------------------------------------------#

    # function that loads the device list from the aux txt file
    def LoadDeviceListFromTxtPremain(self):

        # load the device list
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "device_list_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "device_list_premain.txt"), "r") as f:
                self.device_list = []
                for line in f:
                    self.device_list.append(line.strip())

        # load the working devices
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt"), "r") as f:
                self.working_devices = []
                for line in f:
                    self.working_devices.append(line.strip())

        # load the current accelerator
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt"), "r") as f:
                self.current_accelerator = f.read()

        return

    #----------------------------------------------#

    # function that reads from the json file generated by the pyccda script
    def readPyCCDAJsonFile(self):

        # read pyccda info file
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "pyccda_config.json")):
            with open(os.path.join(self.app_temp_dir, "aux_jsons", "pyccda_config.json")) as f:
                self.pyccda_dictionary = json.load(f)

        return

    #----------------------------------------------#

########################################################
########################################################