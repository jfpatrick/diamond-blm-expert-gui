########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QAbstractTableModel, QEventLoop, QCoreApplication, QTimer, QThread, pyqtSignal, QObject)
from PyQt5.QtWidgets import (QTableView, QSizePolicy, QAbstractItemView, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget, QProgressDialog)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import numpy as np
from general_utils import createCustomTempDir, getSystemTempDir, readJSONConfigFile
import jpype as jp
import json
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import collections

########################################################
########################################################

# GLOBALS

# get real path
REAL_PATH = os.path.realpath(os.path.dirname(__file__))

# ui file
UI_FILENAME = "preview_summary.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"

# constants
JSON_CONFIG_DICT = readJSONConfigFile(os.path.join(REAL_PATH, "config_file.json"))
ACCEPTANCE_FACTOR = float(JSON_CONFIG_DICT["ACCEPTANCE_FACTOR"]) # larger than 1
TURN_TIME_LHC = float(JSON_CONFIG_DICT["TURN_TIME_LHC"]) # microseconds
TURN_TIME_SPS = float(JSON_CONFIG_DICT["TURN_TIME_SPS"]) # microseconds

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

        # this becomes True when 1showup has finished
        self.all_threads_finished = False

        # init table variables
        self.summary_data = None
        self.error_dict = None
        self.summary_header_labels_horizontal = None

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

        return

    #----------------------------------------------#

    # function that receives data from the threads and updates GUI
    def table1ShowUp(self):

        # load data
        self.read1ShowUpJsons()

        # if data received
        if self.error_dict and self.summary_header_labels_horizontal and self.summary_data:

            # transform string keys to integer keys for error_dict
            new_error_dict = {}
            for k1 in self.error_dict.keys():
                new_error_dict[int(k1)] = {}
                for k2 in self.error_dict[k1].keys():
                    new_error_dict[int(k1)][int(k2)] = self.error_dict[k1][k2]
            self.error_dict = new_error_dict

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

            # stop timer
            if self.timer_1_show_up.isActive():
                self.timer_1_show_up.stop()

            # update variable
            self.all_threads_finished = True

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

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

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # set up a timer to load the QThread premain updates
        self.timer_load_txt_with_qthread_premain_updates = QTimer(self)
        self.timer_load_txt_with_qthread_premain_updates.setInterval(1000)
        self.timer_load_txt_with_qthread_premain_updates.timeout.connect(self.updateWorkingModes)
        self.timer_load_txt_with_qthread_premain_updates.start()

        # set up a timer to load 1 SHOW UP table updates from premain
        self.timer_1_show_up = QTimer(self)
        self.timer_1_show_up.setInterval(100)
        self.timer_1_show_up.timeout.connect(self.table1ShowUp)
        self.timer_1_show_up.start()

        return

    #----------------------------------------------#

    # function that updates the working modes
    def updateWorkingModes(self):

        # only update if all threads from the preview_summary.py file finished their jobs
        if self.all_threads_finished:

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

    # function that reads from the json file generated by the pyccda script
    def read1ShowUpJsons(self):

        # read all files
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up")):
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_data.json")):
                with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_data.json")) as f:
                    self.summary_data = json.load(f)
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_header_labels_horizontal.json")):
                with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_header_labels_horizontal.json")) as f:
                    self.summary_header_labels_horizontal = json.load(f)
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "error_dict.json")):
                with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "error_dict.json")) as f:
                    self.error_dict = json.load(f)

        return

    #----------------------------------------------#

########################################################
########################################################