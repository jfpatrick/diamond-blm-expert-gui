########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QAbstractTableModel, QEventLoop, QCoreApplication)
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

########################################################
########################################################

# GLOBALS

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
UI_FILENAME = "preview_summary.ui"
ACCEPTANCE_FACTOR = 1.50
TURN_TIME_LHC = 89.0000 # microseconds
TURN_TIME_SPS = 23.0543 # microseconds

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels_horizontal, header_labels_vertical, errors = [], error_messages = []):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels_horizontal = header_labels_horizontal
        self._header_labels_vertical = header_labels_vertical
        self.errors = errors
        self.error_messages = error_messages

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
        elif role == Qt.ToolTipRole and (row, col) in self.errors and self.error_messages[row]:
            return self.error_messages[row]
        elif role == Qt.ForegroundRole and (row, col) in self.errors:
            if self._data[row][col] == "-":
                return QBrush(QColor("red"))
            else:
                return QBrush(QColor("#FF6C00"))
        elif role == Qt.BackgroundRole and (row, col) in self.errors:
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
        self.error_indexes = []
        self.error_messages = []

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

        # iterate over fields and properties
        for r in range(0, len(self.field_list)+len(self.property_list)):

            # init row list
            row_list = []

            # operate as a field
            if r < len(self.field_list):

                # declare the field
                field = self.field_list[r]

                # append first element which is the field / mode
                row_list.append(str(field))

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
                        except:
                            pass

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        self.error_indexes.append((r, c + 1))
                        self.error_messages.append("")

            # operate as a mode
            else:

                # declare the property
                property = self.property_list[r-len(self.field_list)]

                # skip general information property
                if property == "GeneralInformation":
                    continue

                # get nturns
                try:

                    # in the LHC: 1 turn = 89 microseconds (updates each 1 second if nturn = 11245)
                    # in the SPS: 1 turn = 23.0543 microseconds (updates each 0.1 second if nturn = 4338)
                    if property == "AcquisitionHistogram":
                        nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                    elif property == "AcquisitionIntegral" or property == "AcquisitionIntegralDist" or property == "AcquisitionRawDist":
                        nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
                    elif property == "AcquisitionTurnLoss":
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

                # append first element which is the field / mode
                row_list.append(str(property))

                # iterate over devices
                for c, device in enumerate(self.device_list):

                    # update progress bar
                    self.progress_dialog.setValue(dialog_counter)
                    self.progress_dialog.repaint()
                    self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

                    # if the device IS working
                    if device in self.working_devices:

                        # do a GET request via japc
                        try:
                            field_values = self.japc.getParam("{}/{}".format(device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)
                            row_list.append(str(field_values[1]["acqStamp"]))
                        except self.cern.japc.core.ParameterException as xcp:
                            row_list.append(str(xcp.getMessage()).split(":")[0])
                            self.error_indexes.append((r, c + 1))
                            self.error_messages.append(str(xcp))

                    # if the device IS not working
                    else:

                        # update the list with null information
                        row_list.append("-")
                        self.error_indexes.append((r, c + 1))
                        self.error_messages.append("")

                    # update dialog counter
                    dialog_counter += 1

            # append the row to the full summary data
            self.summary_data.append(row_list)

        # set the header names
        self.summary_header_labels_horizontal = ["Field / Mode"] + self.device_list

        # summary model
        self.model_summary = TableModel(data=self.summary_data, header_labels_horizontal=self.summary_header_labels_horizontal, header_labels_vertical=[], errors=self.error_indexes, error_messages=self.error_messages)
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