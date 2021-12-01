########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QAbstractTableModel)
from PyQt5.QtWidgets import (QSizePolicy, QAbstractItemView, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
from general_utils import createCustomTempDir, getSystemTempDir
import collections
import json
import jpype as jp


########################################################
########################################################

# GLOBALS

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
UI_FILENAME = "preview_one_device.ui"

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
        elif role == Qt.ToolTipRole and self.working_modules_boolean and col == 2:
            return self.errors[row]
        elif role == Qt.ForegroundRole and self.working_modules_boolean and self.errors[row] != "-":
            return QBrush(QColor("red"))
        elif role == Qt.BackgroundRole and self.working_modules_boolean and self.errors[row] != "-":
            return QBrush(QColor("#FFEDED"))

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

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

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
        self.tableView_general_information.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for c in range(0, len(self.general_info_header_labels)):
            self.tableView_general_information.setColumnWidth(c, 300)
        self.tableView_general_information.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView_general_information.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView_general_information.setFocusPolicy(Qt.NoFocus)
        self.tableView_general_information.setSelectionMode(QAbstractItemView.NoSelection)
        self.tableView_general_information.horizontalHeader().setFixedHeight(30)
        self.tableView_general_information.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.tableView_general_information.show()

        # init the data model list for the working modules table
        self.modules_data = []

        # set the header names
        self.modules_header_labels = ["Modes", "Available", "Error", "Last Timestamp"]

        # store full errors
        self.errors = []

        # selectorOverride for the working modules table has to be a specific selector
        selectorOverride = "SPS.USER.SFTPRO1"

        # iterate over properties for the working modules table
        for property in self.property_list:

            # skip general information property
            if property == "GeneralInformation":
                continue

            # get first element to speed it up
            # if self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["scalar"]:
            #     field_to_be_checked = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["scalar"].keys())[0]
            # elif self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["array"]:
            #     field_to_be_checked = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["array"].keys())[0]
            # else:
            #     field_to_be_checked = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["other"].keys())[0]

            # do a GET request via japc
            try:
                field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)
                self.modules_data.append([property, "Yes", "-", "{}".format(str(field_values[1]["acqStamp"]))])
                self.errors.append("-")
            except self.cern.japc.core.ParameterException as xcp:
                self.modules_data.append([property, "No", str(xcp.getMessage()).split(":")[0], "-"])
                self.errors.append(str(xcp))

        # general information model
        self.model_working_modules = TableModel(data = self.modules_data, header_labels = self.modules_header_labels, working_modules_boolean = True, errors = self.errors)
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

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # new device binding
        self.pushButton_open_device.clicked.connect(self.openNewDevice)

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