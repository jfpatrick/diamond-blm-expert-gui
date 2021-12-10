########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QAbstractTableModel, QEventLoop, QCoreApplication, QThread, QTimer, pyqtSignal, QObject)
from PyQt5.QtWidgets import (QTableView, QSizePolicy, QAbstractItemView, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget, QProgressDialog)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
from general_utils import createCustomTempDir, getSystemTempDir, readJSONConfigFile
import collections
import json
import jpype as jp
from datetime import datetime, timedelta, timezone

########################################################
########################################################

# GLOBALS

# ui file
UI_FILENAME = "preview_one_device.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"

# constants
JSON_CONFIG_DICT = readJSONConfigFile(SAVING_PATH)
ACCEPTANCE_FACTOR = float(JSON_CONFIG_DICT["ACCEPTANCE_FACTOR"]) # larger than 1
TURN_TIME_LHC = float(JSON_CONFIG_DICT["TURN_TIME_LHC"]) # microseconds
TURN_TIME_SPS = float(JSON_CONFIG_DICT["TURN_TIME_SPS"]) # microseconds

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels, working_modules_boolean = False, errors = []):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels = header_labels
        self.working_modules_boolean = working_modules_boolean
        self.errors = errors

        return

    def headerData(self, section, orientation, role):

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._header_labels[section]

    def data(self, index, role):

        row = index.row()
        col = index.column()

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif role == Qt.DisplayRole:
            value = self._data[row][col]
            return value
        elif role == Qt.ToolTipRole and self.working_modules_boolean and col == 2 and self.errors[row] != "-":
            return self.errors[row]
        elif role == Qt.ForegroundRole and self.working_modules_boolean and self.errors[row] != "-":
            return QBrush(QColor("#FF6C00"))
        elif role == Qt.BackgroundRole and self.working_modules_boolean and self.errors[row] != "-":
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

        # set the device
        self.current_device = "dBLM.TEST4"
        self.LoadDeviceFromTxtPremain()

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())

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
        self.app.main_window.statusBar().showMessage("Preview of {} loaded!".format(self.current_device), 10*1000)
        self.app.main_window.statusBar().repaint()

        # close progress bar
        if True:
            self.progress_dialog_want_to_close = True
            self.progress_dialog.close()

        return

    #----------------------------------------------#

    # event for closing the window in a right way
    def closeEventProgressDialog(self, evnt):

        # close event
        if self.progress_dialog_want_to_close:
            pass
        else:
            evnt.ignore()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # init progress bar
        if True:
            self.progress_dialog = QProgressDialog("Opening preview for {}...".format(self.current_device), None, 0, len(self.property_list)-1)
            self.progress_dialog.closeEvent = self.closeEventProgressDialog
            self.progress_dialog_want_to_close = False
            self.progress_dialog.setWindowModality(Qt.ApplicationModal)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setWindowTitle("Progress")
            self.progress_dialog.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))
            self.progress_dialog.setValue(0)
            self.progress_dialog.show()
            self.progress_dialog.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

        # initialize widget dicts
        self.labelDict = {}

        # check if the device works
        if self.current_device in self.working_devices:

            # create gui using pyuic5
            self.frame_general_information = QFrame(self.frame_tables)
            self.frame_general_information.setFrameShape(QFrame.NoFrame)
            self.frame_general_information.setFrameShadow(QFrame.Plain)
            self.frame_general_information.setObjectName("frame_general_information")
            self.verticalLayout_frame_general_information = QVBoxLayout(self.frame_general_information)
            self.verticalLayout_frame_general_information.setSpacing(0)
            self.verticalLayout_frame_general_information.setObjectName("verticalLayout_frame_general_information")
            self.label_general_information = QLabel(self.frame_general_information)
            font = QFont()
            font.setBold(True)
            font.setUnderline(False)
            font.setWeight(75)
            self.label_general_information.setText("General Information")
            self.label_general_information.setFont(font)
            self.label_general_information.setAlignment(Qt.AlignCenter)
            self.label_general_information.setObjectName("label_general_information")
            self.label_general_information.setStyleSheet("background-color: rgb(216, 216, 216);")
            self.label_general_information.setFrameShape(QFrame.StyledPanel)
            self.label_general_information.setFrameShadow(QFrame.Plain)
            self.label_general_information.setMinimumSize(30, 30)
            self.verticalLayout_frame_general_information.addWidget(self.label_general_information)
            self.tableView_general_information = QTableView(self.frame_general_information)
            self.tableView_general_information.setStyleSheet("QTableView{\n"
                                                             "    background-color: rgb(243, 243, 243);\n"
                                                             "    margin-top: 0;\n"
                                                             "}")
            self.tableView_general_information.setFrameShape(QFrame.StyledPanel)
            self.tableView_general_information.setFrameShadow(QFrame.Plain)
            self.tableView_general_information.setDragEnabled(False)
            self.tableView_general_information.setAlternatingRowColors(True)
            self.tableView_general_information.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableView_general_information.setShowGrid(True)
            self.tableView_general_information.setGridStyle(Qt.SolidLine)
            self.tableView_general_information.setObjectName("tableView_general_information")
            self.tableView_general_information.horizontalHeader().setHighlightSections(False)
            self.tableView_general_information.horizontalHeader().setMinimumSectionSize(50)
            self.tableView_general_information.horizontalHeader().setStretchLastSection(True)
            self.tableView_general_information.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.tableView_general_information.verticalHeader().setVisible(False)
            self.tableView_general_information.verticalHeader().setDefaultSectionSize(50)
            self.tableView_general_information.verticalHeader().setHighlightSections(False)
            self.tableView_general_information.verticalHeader().setMinimumSectionSize(25)
            self.verticalLayout_frame_general_information.addWidget(self.tableView_general_information)
            self.horizontalLayout_frame_tables.addWidget(self.frame_general_information)
            self.frame_working_devices = QFrame(self.frame_tables)
            self.frame_working_devices.setFrameShape(QFrame.NoFrame)
            self.frame_working_devices.setFrameShadow(QFrame.Plain)
            self.frame_working_devices.setObjectName("frame_working_devices")
            self.verticalLayout_frame_general_information_2 = QVBoxLayout(self.frame_working_devices)
            self.verticalLayout_frame_general_information_2.setSpacing(0)
            self.verticalLayout_frame_general_information_2.setObjectName("verticalLayout_frame_general_information_2")
            self.label_working_devices = QLabel(self.frame_working_devices)
            font = QFont()
            font.setBold(True)
            font.setUnderline(False)
            font.setWeight(75)
            self.label_working_devices.setText("Working Modes")
            self.label_working_devices.setFont(font)
            self.label_working_devices.setAlignment(Qt.AlignCenter)
            self.label_working_devices.setObjectName("label_working_devices")
            self.label_working_devices.setStyleSheet("background-color: rgb(216, 216, 216);")
            self.label_working_devices.setFrameShape(QFrame.StyledPanel)
            self.label_working_devices.setFrameShadow(QFrame.Plain)
            self.label_working_devices.setMinimumSize(30, 30)
            self.verticalLayout_frame_general_information_2.addWidget(self.label_working_devices)
            self.tableView_working_modules = QTableView(self.frame_working_devices)
            self.tableView_working_modules.setStyleSheet("QTableView{\n"
                                                         "    background-color: rgb(243, 243, 243);\n"
                                                         "    margin-top: 0;\n"
                                                         "}")
            self.tableView_working_modules.setFrameShape(QFrame.StyledPanel)
            self.tableView_working_modules.setFrameShadow(QFrame.Plain)
            self.tableView_working_modules.setDragEnabled(False)
            self.tableView_working_modules.setAlternatingRowColors(True)
            self.tableView_working_modules.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableView_working_modules.setShowGrid(True)
            self.tableView_working_modules.setGridStyle(Qt.SolidLine)
            self.tableView_working_modules.setSortingEnabled(False)
            self.tableView_working_modules.setWordWrap(True)
            self.tableView_working_modules.setCornerButtonEnabled(True)
            self.tableView_working_modules.setObjectName("tableView_working_modules")
            self.tableView_working_modules.horizontalHeader().setHighlightSections(False)
            self.tableView_working_modules.horizontalHeader().setMinimumSectionSize(50)
            self.tableView_working_modules.horizontalHeader().setStretchLastSection(False)
            self.tableView_working_modules.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.tableView_working_modules.verticalHeader().setVisible(False)
            self.tableView_working_modules.verticalHeader().setDefaultSectionSize(50)
            self.tableView_working_modules.verticalHeader().setHighlightSections(False)
            self.tableView_working_modules.verticalHeader().setMinimumSectionSize(25)
            self.verticalLayout_frame_general_information_2.addWidget(self.tableView_working_modules)
            self.horizontalLayout_frame_tables.addWidget(self.frame_working_devices)

            # selectorOverride for GeneralInformation should be empty
            selectorOverride = ""

            # get field values via pyjapc
            field_values = self.japc.getParam("{}/{}".format(self.current_device, "GeneralInformation"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # convert all elements to string
            field_values = {k: str(v) if k != "monitorNames" else v for k, v in field_values.items()}

            # if the dict has a monitorNames field, process the string a little bit for the sake of aesthetics
            if "monitorNames" in field_values.keys():
                final_field_value = ""
                new_val = field_values["monitorNames"]
                for i in range(0, len(new_val)):
                    string = new_val[i]
                    if i > 0:
                        final_field_value = final_field_value + ", " + string
                    else:
                        final_field_value = string
                final_field_value = "  {}  ".format(final_field_value)
                field_values["monitorNames"] = final_field_value

            # uppercase MonitorNames
            field_values["MonitorNames"] = field_values.pop("monitorNames")

            # sort the dict
            field_values = collections.OrderedDict(sorted(field_values.items()))

            # convert the dict into a list of lists
            self.general_information_data = list(map(list, field_values.items()))

            # set the header names
            self.general_info_header_labels = ["Fields", "Values"]

            # general information model
            self.model_general_information = TableModel(data = self.general_information_data, header_labels = self.general_info_header_labels)
            self.tableView_general_information.setModel(self.model_general_information)
            self.tableView_general_information.update()
            self.tableView_general_information.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableView_general_information.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableView_general_information.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tableView_general_information.setFocusPolicy(Qt.NoFocus)
            self.tableView_general_information.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableView_general_information.horizontalHeader().setFixedHeight(30)
            self.tableView_general_information.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
            self.tableView_general_information.show()

            # init the data model dict for the working modules table
            self.modules_data = {}

            # set the header names
            self.modules_header_labels = ["Modes", "Running", "Info", "Last Timestamp"]

            # store full errors
            self.errors = {}

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

            # counter for the dialog progress bar
            dialog_counter = 0

            # iterate over properties for the working modules table
            for property in self.property_list:

                # skip general information property
                if property == "GeneralInformation":
                    continue

                # update progress bar
                if True:
                    self.progress_dialog.setValue(dialog_counter)
                    self.progress_dialog.repaint()
                    self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

                # get nturns
                try:

                    # in the LHC: 1 turn = 89 microseconds (updates each 1 second if nturn = 11245)
                    # in the SPS: 1 turn = 23.0543 microseconds (updates each 0.1 second if nturn = 4338)
                    if property == "AcquisitionHistogram":
                        is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossHistogramSetting"]["mux"]
                        if is_multiplexed == "False":
                            selectorOverride = ""
                        nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                    elif property == "AcquisitionIntegral" or property == "AcquisitionIntegralDist" or property == "AcquisitionRawDist":
                        is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossIntegralSetting"]["mux"]
                        if is_multiplexed == "False":
                            selectorOverride = ""
                        nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                    elif property == "AcquisitionTurnLoss":
                        is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["TurnLossMeasurementSetting"]["mux"]
                        if is_multiplexed == "False":
                            selectorOverride = ""
                        nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "TurnLossMeasurementSetting", "turnTrackCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
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
                except:

                    # pass
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
                    field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)

                    # get timestamps
                    get_ts = field_values[1]["acqStamp"]
                    current_ts = datetime.now(timezone.utc)

                    # for the capture do not care about timestamps
                    if property == "Capture":

                        # if the buffer is not empty
                        if field_values[0]["rawBuf0"].size > 0:

                            # if the try did not give an error then it is working
                            self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                            self.errors[property] = "-"

                        # if buffers are empty show a custom error
                        else:

                            # BUFFERS_ARE_EMPTY
                            self.modules_data[property] = [property, "No", "BUFFERS_ARE_EMPTY", "{}".format(str(get_ts))]
                            self.errors[property] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

                    # for the others we should care about timestamps
                    else:

                        # show a custom error if nturns is 0
                        if nturns == 0:

                            # NTURNS_IS_ZERO
                            self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
                            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

                        # normal procedure
                        else:

                            # compare timestamps
                            if current_ts - get_ts < timedelta(seconds = turn_time_in_seconds * ACCEPTANCE_FACTOR):
                                self.modules_data[property] = [property, "-", "MODE_BEING_ANALYZED", "{}".format(str(get_ts))]
                                self.errors[property] = "custom.message.error: MODE_BEING_ANALYZED: The mode {} is still being analyzed in a different thread. Wait a few seconds until a decision about its availability is made.".format(property)
                            else:
                                self.modules_data[property] = [property, "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds*ACCEPTANCE_FACTOR, current_ts)

                # this exception is usually NO_DATA_AVAILABLE_FOR_USER (happens when it is not initialized yet)
                except self.cern.japc.core.ParameterException as xcp:

                    # NO_DATA_AVAILABLE_FOR_USER
                    self.modules_data[property] = [property, "No", str(xcp.getMessage()).split(":")[0], "-"]
                    self.errors[property] = str(xcp)

                # update dialog counter
                dialog_counter += 1

            # working modes model
            self.model_working_modules = TableModel(data = list(self.modules_data.values()), header_labels = self.modules_header_labels, working_modules_boolean = True, errors = list(self.errors.values()))
            self.tableView_working_modules.setModel(self.model_working_modules)
            self.tableView_working_modules.update()
            self.tableView_working_modules.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            for c in range(0, len(self.modules_header_labels)):
                self.tableView_working_modules.setColumnWidth(c, 150)
            self.tableView_working_modules.horizontalHeader().setStretchLastSection(True)
            self.tableView_working_modules.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableView_working_modules.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tableView_working_modules.setFocusPolicy(Qt.NoFocus)
            self.tableView_working_modules.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableView_working_modules.horizontalHeader().setFixedHeight(30)
            self.tableView_working_modules.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
            self.tableView_working_modules.show()

            # enable open button
            self.pushButton_open_device.setEnabled(True)

        # if the device does not work
        else:

            # create gui using pyuic5
            self.frame_not_working = QFrame(self.frame_tables)
            self.frame_not_working.setStyleSheet("QFrame{\n"
                                                 "    background-color: rgb(243, 243, 243);\n"
                                                 "}")
            self.frame_not_working.setFrameShape(QFrame.StyledPanel)
            self.frame_not_working.setFrameShadow(QFrame.Plain)
            self.frame_not_working.setObjectName("frame_not_working")
            self.verticalLayout_frame_not_working = QVBoxLayout(self.frame_not_working)
            self.verticalLayout_frame_not_working.setObjectName("verticalLayout_frame_not_working")
            self.horizontalLayout_frame_tables.addWidget(self.frame_not_working)

            # just show the not working message
            self.labelDict["label_not_working_device"] = QLabel(self.frame_not_working)
            self.labelDict["label_not_working_device"].setObjectName("label_not_working_device")
            self.labelDict["label_not_working_device"].setAlignment(Qt.AlignCenter)
            self.labelDict["label_not_working_device"].setWordWrap(True)
            self.labelDict["label_not_working_device"].setTextFormat(Qt.RichText)
            self.labelDict["label_not_working_device"].setText("<font color=red>NOT WORKING DEVICE - {}</font>".format(self.possible_exception))
            self.labelDict["label_not_working_device"].setStyleSheet("border: 0px solid black; margin: 100px;")
            self.labelDict["label_not_working_device"].setMinimumSize(QSize(120, 32))
            self.verticalLayout_frame_not_working.addWidget(self.labelDict["label_not_working_device"])

            # disable open button
            self.pushButton_open_device.setEnabled(False)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # new device binding
        self.pushButton_open_device.clicked.connect(self.openNewDevice)

        # set up a timer to load the QThread premain updates
        self.timer_load_txt_with_qthread_premain_updates = QTimer(self)
        self.timer_load_txt_with_qthread_premain_updates.setInterval(500)
        self.timer_load_txt_with_qthread_premain_updates.timeout.connect(self.updateWorkingModes)
        self.timer_load_txt_with_qthread_premain_updates.start()

        return

    #----------------------------------------------#

    # function that updates the working modes
    def updateWorkingModes(self):

        # check device is working
        if self.current_device in self.working_devices:

            # check dirs exist
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_for_preview_one_device.json")) and os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_for_preview_one_device.json")):

                # load the new data
                with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_for_preview_one_device.json")) as f:
                    modules_data_new = json.load(f)
                with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_for_preview_one_device.json")) as f:
                    errors_new = json.load(f)

                # if there were no changes just skip
                if self.modules_data == modules_data_new:

                    # skip
                    return

                # normal procedure
                else:

                    # update variables
                    if len(self.modules_data) == len(modules_data_new):
                        self.modules_data = modules_data_new
                        self.errors = errors_new
                    else:
                        for key in modules_data_new.keys():
                            self.modules_data[key] = modules_data_new[key]
                            self.errors[key] = errors_new[key]

                    # working modes model
                    self.model_working_modules = TableModel(data=list(self.modules_data.values()), header_labels=self.modules_header_labels, working_modules_boolean=True, errors=list(self.errors.values()))
                    self.tableView_working_modules.setModel(self.model_working_modules)
                    self.tableView_working_modules.update()

        return

    #----------------------------------------------#

    # function that overwrites the txt file so that the premain.py can open the new device panel
    def openNewDevice(self):

        # print the OPEN DEVICE action
        print("{} - Button OPEN DEVICE pressed".format(UI_FILENAME))

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # write the file
        with open(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt"), "w") as f:
            f.write("True")

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxtPremain(self):

        # load the selected device
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt"), "r") as f:
                self.current_device = f.read()

        # load the acc
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt"), "r") as f:
                self.current_accelerator = f.read()

        # load the exception if any
        self.possible_exception = ""
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "exception_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "exception_premain.txt"), "r") as f:
                self.possible_exception = f.read()

        # load the working devices
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt"), "r") as f:
                self.working_devices = []
                for line in f:
                    self.working_devices.append(line.strip())

        # load the preloaded devices
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "preloaded_devices_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "preloaded_devices_premain.txt"), "r") as f:
                self.preloaded_devices = []
                for line in f:
                    self.preloaded_devices.append(line.strip())

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