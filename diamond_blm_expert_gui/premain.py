########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, CContextFrame, CApplication, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QBrush, QPixmap, QFont)
from PyQt5.QtCore import (QSize, Qt, QTimer, QThread, pyqtSignal, QObject, QEventLoop, QCoreApplication, QRect, QAbstractTableModel)
from PyQt5.QtWidgets import (QSplitter, QHeaderView, QTableView, QGroupBox, QSpacerItem, QFrame, QSizePolicy, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget, QProgressDialog, QScrollArea, QPushButton, QAbstractItemView, QAbstractScrollArea)
from PyQt5.Qt import QItemSelectionModel, QMenu

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyccda
import pyjapc
import jpype as jp
from create_pyccda_json_file import create_pyccda_json_file
import json
import numpy as np
import shutil
import faulthandler
from general_utils import createCustomTempDir, getSystemTempDir, removeAppDir, readJSONConfigFile
from datetime import datetime, timedelta, timezone
import collections
import random
import signal

########################################################
########################################################

# THIS IS TO MAKE SURE WE ONLY HAVE ONE INSTANCE OF THE APPLICATION RUNNING AT THE SAME TIME!

# from tendo import singleton

# try:
#     current_instance = singleton.SingleInstance()
# except singleton.SingleInstanceException as xcp:
#     print("Application is already running on another instance. Please, make sure only one instance is running at the same time. Otherwise, it won't open properly.")
#     sys.exit(0)

import socket
from contextlib import closing

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

temp_system_dir = getSystemTempDir()
if not os.path.exists(os.path.join(temp_system_dir, 'free_ports.txt')):
    free_port_list = []
    for i in range(0, 50):
        free_port = find_free_port()
        free_port_list.append(free_port)
    free_port_list.sort()
    with open(os.path.join(temp_system_dir, 'free_ports.txt'), 'w') as f:
        for item in free_port_list:
            f.write("%s\n" % item)
sleep(1)
with open(os.path.join(temp_system_dir, 'free_ports.txt')) as f:
    free_port_list = f.readlines()

socket_object = socket.socket()
host = socket.gethostname()
free_port = int(free_port_list[0])
try:
    socket_object.bind((host, free_port))
except OSError as xcp:
    print("[{}] Application is already running on another instance. Please, make sure only one instance is running at the same time. Otherwise, it won't open properly.".format(free_port))
    sys.exit(0)

########################################################
########################################################

# GLOBALS

# ui file
UI_FILENAME = "premain.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"

# constants
JSON_CONFIG_DICT = readJSONConfigFile(name_of_file = "config_file.json")
RECHECK_DEVICES_PERIOD = float(JSON_CONFIG_DICT["RECHECK_DEVICES_PERIOD"]) # each 1 minute
ACCEPTANCE_FACTOR = float(JSON_CONFIG_DICT["ACCEPTANCE_FACTOR"]) # larger than 1
TURN_TIME_LHC = float(JSON_CONFIG_DICT["TURN_TIME_LHC"]) # microseconds
TURN_TIME_SPS = float(JSON_CONFIG_DICT["TURN_TIME_SPS"]) # microseconds

# query for the devices
QUERY = '((global==false) and (deviceClassInfo.name=="BLMDIAMONDVFC") and (timingDomain=="LHC" or timingDomain=="SPS")) or (name=="*dBLM.TEST*")'

# others
SHOW_COMMANDS_IN_SETTINGS = False
LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY = {}
DATA_SUBS_SUMMARY = {}

########################################################
########################################################

# util function
def can_be_converted_to_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels, titles_set_window = False, three_column_window = False):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels = header_labels
        self.titles_set_window = titles_set_window
        self.three_column_window = three_column_window

        return

    def headerData(self, section, orientation, role):

        if self._header_labels:
            if role == Qt.DisplayRole:
                if orientation == Qt.Horizontal:
                    return self._header_labels[section]

    def data(self, index, role):

        row = index.row()
        col = index.column()

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data[row][col]
            return value
        elif role == Qt.BackgroundRole:
            if self.titles_set_window:
                return QBrush(QColor("#d2d2d2"))
            if self.three_column_window and col == 2:
                return QBrush(QColor("#ffffff"))

    def rowCount(self, index):

        return len(self._data)

    def columnCount(self, index):

        return len(self._data[0])

    def flags(self, index):

        if index.column() == 2:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):

        if role == Qt.EditRole and index.column() == 2:
            self._data[index.row()][index.column()] = value
            return True

        return False

########################################################
########################################################

class DialogThreeColumnSet(QDialog):

    #----------------------------------------------#

    # signals
    nturns_changed = pyqtSignal(bool)

    #----------------------------------------------#

    def __init__(self, parent = None):

        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # save the parent
        self.dialog_parent = parent

        # inherit from QDialog
        QDialog.__init__(self, parent)

        # retrieve the attributes
        self.pyccda_dictionary = parent.pyccda_dictionary
        self.app = parent.app
        self.property_list = parent.property_list
        self.current_device = parent.current_device
        self.current_accelerator = parent.current_accelerator
        self.current_selector = parent.current_selector
        self.field_dict = parent.field_dict
        self.japc = parent.japc
        self.field_values_macro_dict = parent.field_values_macro_dict

        # when you want to destroy the dialog set this to True
        self._want_to_close = False

        # set the window title and build the GUI
        self.setWindowTitle("DIAMOND BLM SETTINGS")
        self.buildCodeWidgets()
        self.bindWidgets()

        return

    #----------------------------------------------#

    # event for closing the window in a right way
    def closeEvent(self, evnt):

        # close event
        if self._want_to_close:
            super(DialogThreeColumnSet, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setVisible(False)

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # initialize widget dicts
        self.groupBoxDict = {}
        self.layoutDict = {}
        self.labelDict = {}
        self.lineEditDict = {}
        self.commandButtonDict = {}
        self.tableViewDict = {}
        self.dataTableModelDict = {}
        self.dataModelDict = {}

        # resize the dialog window
        self.resize(400, 800)

        # vertical layout of the main form of the dialog
        self.vertical_layout_main_dialog = QVBoxLayout(self)
        self.vertical_layout_main_dialog.setObjectName("vertical_layout_main_dialog")
        self.vertical_layout_main_dialog.setContentsMargins(6, 20, 6, 6)
        self.vertical_layout_main_dialog.setSpacing(2)

        # create the main frame
        self.frame_properties = QFrame(self)
        self.frame_properties.setObjectName("frame_properties")
        self.frame_properties.setFrameShape(QFrame.NoFrame)
        self.frame_properties.setFrameShadow(QFrame.Raised)

        # vertical layout of the frame
        self.vertical_layout_main_frame = QVBoxLayout(self.frame_properties)
        self.vertical_layout_main_frame.setObjectName("vertical_layout_main_frame")

        # scrolling area
        self.scrollArea_properties = QScrollArea(self.frame_properties)
        self.scrollArea_properties.setObjectName("scrollArea_properties")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_properties.sizePolicy().hasHeightForWidth())
        self.scrollArea_properties.setSizePolicy(sizePolicy)
        self.scrollArea_properties.setFrameShadow(QFrame.Plain)
        self.scrollArea_properties.setLineWidth(1)
        self.scrollArea_properties.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_properties.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_properties.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.scrollArea_properties.setWidgetResizable(True)
        self.scrollArea_properties.setAlignment(Qt.AlignCenter)

        # scrolling contents
        self.scrollingContents_properties = QWidget()
        self.scrollingContents_properties.setObjectName("scrollingContents_properties")
        self.scrollingContents_properties.setGeometry(QRect(0, 340, 594, 75))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollingContents_properties.sizePolicy().hasHeightForWidth())
        self.scrollingContents_properties.setSizePolicy(sizePolicy)

        # vertical layout fro the scrollingContents_properties
        self.verticalLayout_scrollingContents_properties = QVBoxLayout(self.scrollingContents_properties)
        self.verticalLayout_scrollingContents_properties.setObjectName("verticalLayout_scrollingContents_properties")

        # link the scrollingContents_properties with the scrollArea_properties and add the layouts
        self.scrollArea_properties.setWidget(self.scrollingContents_properties)
        self.vertical_layout_main_frame.addWidget(self.scrollArea_properties)
        self.vertical_layout_main_dialog.addWidget(self.frame_properties)

        # create the get set frame (even though it will only be a set button)
        self.frame_get_set = QFrame(self)
        self.frame_get_set.setObjectName("frame_get_set")
        self.frame_get_set.setFrameShape(QFrame.NoFrame)
        self.frame_get_set.setFrameShadow(QFrame.Plain)

        # layout for the frame_get_set
        self.horizontalLayout_frame_get_set = QHBoxLayout(self.frame_get_set)
        self.horizontalLayout_frame_get_set.setObjectName("horizontalLayout_frame_get_set")
        self.horizontalLayout_frame_get_set.setContentsMargins(9, 0, 9, -1)
        self.horizontalLayout_frame_get_set.setSpacing(16)

        # invisible scrollArea
        self.scrollArea_get_set = QScrollArea(self.frame_get_set)
        self.scrollArea_get_set.setObjectName("scrollArea_get_set")
        self.scrollArea_get_set.setStyleSheet("background-color: transparent;")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_get_set.sizePolicy().hasHeightForWidth())
        self.scrollArea_get_set.setSizePolicy(sizePolicy)
        self.scrollArea_get_set.setFrameShape(QFrame.NoFrame)
        self.scrollArea_get_set.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_get_set.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_get_set.setWidgetResizable(True)
        self.scrollArea_get_set.setAlignment(Qt.AlignCenter)

        # make the scroll bar of the get and set panel invisible
        sp_scroll_area_get_set = self.scrollArea_get_set.verticalScrollBar().sizePolicy()
        sp_scroll_area_get_set.setRetainSizeWhenHidden(True)
        self.scrollArea_get_set.verticalScrollBar().setSizePolicy(sp_scroll_area_get_set)
        self.scrollArea_get_set.verticalScrollBar().hide()

        # invisible scrollingContents
        self.scrollingContents_get_set = QWidget()
        self.scrollingContents_get_set.setObjectName("scrollingContents_get_set")
        self.scrollingContents_get_set.setGeometry(QRect(0, 0, 1276, 68))

        # layout for scrollingContents_get_set
        self.horizontalLayout_scrollingContents_get_set = QHBoxLayout(self.scrollingContents_get_set)
        self.horizontalLayout_scrollingContents_get_set.setObjectName("horizontalLayout_scrollingContents_get_set")

        # add a spacer
        spacerItem_1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_scrollingContents_get_set.addItem(spacerItem_1)

        # font for pushbutton
        font_for_pushbutton = QFont()
        font_for_pushbutton.setBold(True)
        font_for_pushbutton.setWeight(75)

        # create set pushbutton
        self.pushButton_set = QPushButton(self.scrollingContents_get_set)
        self.pushButton_set.setObjectName("pushButton_set")
        self.pushButton_set.setMinimumSize(QSize(100, 32))
        self.pushButton_set.setFont(font_for_pushbutton)
        self.pushButton_set.setText("SET")

        # add it to the layout
        self.horizontalLayout_scrollingContents_get_set.addWidget(self.pushButton_set)

        # add another spacer
        spacerItem_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_scrollingContents_get_set.addItem(spacerItem_2)

        # link the rest of items
        self.scrollArea_get_set.setWidget(self.scrollingContents_get_set)
        self.horizontalLayout_frame_get_set.addWidget(self.scrollArea_get_set)

        # add everything to the vertical layout of the main form
        self.vertical_layout_main_dialog.addWidget(self.frame_get_set)
        self.vertical_layout_main_dialog.setStretch(0, 95)
        self.vertical_layout_main_dialog.setStretch(1, 5)

        # read and apply the qss files
        with open("qss/scrollArea_properties.qss", "r") as fh:
            self.scrollArea_properties.setStyleSheet(fh.read())
        with open("qss/scrollingContents_properties.qss", "r") as fh:
            self.scrollingContents_properties.setStyleSheet(fh.read())
        with open("qss/pushButton_set.qss", "r") as fh:
            self.pushButton_set.setStyleSheet(fh.read())

        # set groupbox for the titles of the labels
        self.groupBox_for_titles = QGroupBox(self.scrollingContents_properties)
        self.groupBox_for_titles.setObjectName("groupBox_for_titles")
        self.groupBox_for_titles.setAlignment(Qt.AlignCenter)
        self.groupBox_for_titles.setFlat(True)
        self.groupBox_for_titles.setCheckable(False)
        self.groupBox_for_titles.setTitle("")
        self.horizontal_layout_groupBox_for_titles = QHBoxLayout(self.groupBox_for_titles)
        self.horizontal_layout_groupBox_for_titles.setObjectName("horizontal_layout_groupBox_for_titles")

        # set table titles
        self.tableViewDict["titles"] = QTableView(self.groupBox_for_titles)
        self.tableViewDict["titles"].setStyleSheet("QTableView{\n"
                                                   "    background-color: rgb(243, 243, 243);\n"
                                                   "    margin-top: 0;\n"
                                                   "}")
        self.tableViewDict["titles"].setFrameShape(QFrame.StyledPanel)
        self.tableViewDict["titles"].setFrameShadow(QFrame.Plain)
        self.tableViewDict["titles"].setDragEnabled(False)
        self.tableViewDict["titles"].setAlternatingRowColors(True)
        self.tableViewDict["titles"].setSelectionMode(QAbstractItemView.NoSelection)
        self.tableViewDict["titles"].setShowGrid(True)
        self.tableViewDict["titles"].setGridStyle(Qt.SolidLine)
        self.tableViewDict["titles"].setObjectName("tableView_general_information")
        self.tableViewDict["titles"].horizontalHeader().setVisible(False)
        self.tableViewDict["titles"].horizontalHeader().setHighlightSections(False)
        self.tableViewDict["titles"].verticalHeader().setDefaultSectionSize(0)
        self.tableViewDict["titles"].horizontalHeader().setMinimumSectionSize(0)
        self.tableViewDict["titles"].horizontalHeader().setStretchLastSection(True)
        self.tableViewDict["titles"].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.tableViewDict["titles"].verticalHeader().setVisible(False)
        self.tableViewDict["titles"].verticalHeader().setDefaultSectionSize(25)
        self.tableViewDict["titles"].verticalHeader().setHighlightSections(False)
        self.tableViewDict["titles"].verticalHeader().setMinimumSectionSize(25)
        self.tableViewDict["titles"].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableViewDict["titles"].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableViewDict["titles"].setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableViewDict["titles"].setFocusPolicy(Qt.NoFocus)
        self.tableViewDict["titles"].setSelectionMode(QAbstractItemView.NoSelection)
        self.tableViewDict["titles"].horizontalHeader().setFixedHeight(0)
        self.tableViewDict["titles"].horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.tableViewDict["titles"].show()
        self.horizontal_layout_groupBox_for_titles.addWidget(self.tableViewDict["titles"])
        self.dataTableModelDict["titles"] = TableModel(data=[["Name", "Current Value", "New Value"]], header_labels=[], titles_set_window = True)
        self.tableViewDict["titles"].setModel(self.dataTableModelDict["titles"])
        self.tableViewDict["titles"].update()
        self.groupBox_for_titles.setFixedHeight(int(25 * (1 + 2)))
        self.verticalLayout_scrollingContents_properties.addWidget(self.groupBox_for_titles)

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # create the group boxes
        for property in self.property_list:

            # init data list
            self.dataModelDict[property] = []

            # property groupbox
            self.groupBoxDict["{}".format(property)] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format(property)].setObjectName("groupBox_{}".format(property))
            self.groupBoxDict["{}".format(property)].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format(property)].setFlat(True)
            self.groupBoxDict["{}".format(property)].setCheckable(False)
            self.groupBoxDict["{}".format(property)].setTitle("{}".format(property))
            self.groupBoxDict["{}".format(property)].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format(property)])

            # property layout
            self.layoutDict["groupBox_{}".format(property)] = QGridLayout(self.groupBoxDict["{}".format(property)])
            self.layoutDict["groupBox_{}".format(property)].setObjectName("layout_groupBox_{}".format(property))

            # create table
            self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
            self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                       "    background-color: rgb(243, 243, 243);\n"
                                                       "    margin-top: 0;\n"
                                                       "}")
            self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
            self.tableViewDict[property].setFrameShadow(QFrame.Plain)
            self.tableViewDict[property].setDragEnabled(False)
            self.tableViewDict[property].setAlternatingRowColors(True)
            self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
            self.tableViewDict[property].setShowGrid(True)
            self.tableViewDict[property].setGridStyle(Qt.SolidLine)
            self.tableViewDict[property].setObjectName("tableView_general_information")
            self.tableViewDict[property].horizontalHeader().setVisible(False)
            self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
            self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
            self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
            self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
            self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.tableViewDict[property].verticalHeader().setVisible(False)
            self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
            self.tableViewDict[property].verticalHeader().setHighlightSections(False)
            self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
            self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
            self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
            self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
            self.tableViewDict[property].horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
            self.tableViewDict[property].show()
            self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

            # fill table
            for field in self.field_dict[property]:
                self.dataModelDict[property].append([str(field), str(self.field_values_macro_dict["{}".format(property)][field]), str(self.field_values_macro_dict["{}".format(property)][field])])

            # update model
            self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[], three_column_window = True)
            self.tableViewDict[property].setModel(self.dataTableModelDict[property])
            self.tableViewDict[property].update()

            # update groupbox size in function of the number of rows
            self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        return

    #----------------------------------------------#

    # function that handles japc and UI stuff when rbac is disconnected
    def rbacLogoutSucceeded(self):

        # print message
        print("{} - RBAC logout succeeded...".format(UI_FILENAME))

        # end pyjapc rbac connection
        self.japc.rbacLogout()

        return

    #----------------------------------------------#

    # this function gets activated whenever RBAC logins successfully
    def rbacLoginSucceeded(self):

        # print message
        print("{} - RBAC login succeeded...".format(UI_FILENAME))

        # save the token into the environmental variable so that we can read it with pyjapc
        os.environ["RBAC_TOKEN_SERIALIZED"] = self.app._rbac.serialized_token

        # now that we have a token try to login with japc too
        self.japc.rbacLogin(readEnv=True)

        return

    #----------------------------------------------#

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # print
        print("{} - New selector is: {}".format(UI_FILENAME, self.current_selector))

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET#2 pressed".format(UI_FILENAME))

        # init lists
        list_areAllFieldsJustTheSame = []
        list_dict_to_inject = []
        list_needs_warning_message_box = []
        list_mux = []
        nturn_changed = False

        # boolean
        types_are_wrong = False

        # iterate over all properties
        for property in self.property_list:

            # create dictionary to inject
            dict_to_inject = {}

            # init the boolean
            areAllFieldsJustTheSame = True

            # iterate over all fields
            for field_counter, field in enumerate(self.field_dict["{}".format(property)]):

                # compare old and new values
                old_value = self.field_values_macro_dict["{}".format(property)]["{}".format(field)]
                new_value = self.tableViewDict[property].model()._data[field_counter][2]

                # check if both are booleans
                if str(old_value) == "True" or str(old_value) == "False":
                    if str(new_value) != "True" and str(new_value) != "False":
                        types_are_wrong = True

                # check types are the same
                if can_be_converted_to_float(str(old_value)) != can_be_converted_to_float(str(new_value)) or types_are_wrong:

                    # if the input type does not match with the field type just show an error and return
                    message_title = "WARNING"
                    message_text = "Please check that variable types are the same!"
                    self.message_box = QMessageBox.warning(self, message_title, message_text)

                    # break the set action
                    return

                # if at least one field is different, do a SET of the whole dictionary
                if str(old_value) != str(new_value):
                    areAllFieldsJustTheSame = False

                # check nturns
                if field == "blmNTurn" or field == "turnAvgCnt" or field == "turnTrackCnt":
                    if not areAllFieldsJustTheSame:
                        nturn_changed = True

                # inject the value
                dict_to_inject["{}".format(field)] = new_value

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # append the values
            if is_multiplexed == "True" and areAllFieldsJustTheSame == False:
                list_needs_warning_message_box.append(True)
            else:
                list_needs_warning_message_box.append(False)
            list_areAllFieldsJustTheSame.append(areAllFieldsJustTheSame)
            list_dict_to_inject.append(dict_to_inject)
            list_mux.append(is_multiplexed)

        # determine if there were changes that require a non-generic selector
        muxAndNotEmpty = any(list_needs_warning_message_box)

        # check if the selector is generic
        if self.current_selector:
            isAllOrEmptySelector = self.current_selector.split(".")[-1] == "ALL"
        else:
            isAllOrEmptySelector = True

        # if the current selector is generic and there were changes on a non-mux channel, force the user to use a non-generic selector
        if muxAndNotEmpty and isAllOrEmptySelector:

            # show warning message
            message_title = "WARNING"
            message_text = "You are trying to do a SET on a multiplexed property with the generic {} selector. Please select a specific USER if you wish to modify this field.".format(self.current_selector)
            self.message_box = QMessageBox.warning(self, message_title, message_text)

            # break the set action
            return

        # otherwise continue as normal
        else:

            # iterate over all properties
            for count_prop, property in enumerate(self.property_list):

                # if no changes
                if list_areAllFieldsJustTheSame[count_prop]:

                    # just continue
                    continue

                # if there were changes
                else:

                    # set the param
                    if list_mux[count_prop] == "True":
                        self.japc.setParam("{}/{}".format(self.current_device, property), list_dict_to_inject[count_prop], timingSelectorOverride = self.current_selector)
                    else:
                        self.japc.setParam("{}/{}".format(self.current_device, property), list_dict_to_inject[count_prop], timingSelectorOverride = "")

        # update values in the parent panel
        self.dialog_parent.getFunction(show_message = False)

        # close the dialog
        sleep(0.1)
        self._want_to_close = True
        self.close()
        self.deleteLater()

        # do another get
        if muxAndNotEmpty:
            self.dialog_parent.getFunction(show_message = False)

        # status bar message
        self.app.main_window.statusBar().showMessage("Command SET ran successfully!", 3*1000)
        self.app.main_window.statusBar().repaint()

        # emit the signal if there has been changes to the nturns
        if nturn_changed:
            self.nturns_changed.emit(True)

        return

    #----------------------------------------------#

########################################################
########################################################

class SettingsDialogAuto(QDialog):

    #----------------------------------------------#

    # signals
    nturns_changed = pyqtSignal(bool)

    #----------------------------------------------#

    # init function
    def __init__(self, parent = None):

        # save the parent
        self.dialog_parent = parent

        # inherit from QDialog
        QDialog.__init__(self, parent)

        # retrieve the attributes
        self.app_temp_dir = parent.app_temp_dir
        self.app = parent.app
        self.pyccda_dictionary = parent.pyccda_dictionary
        self.current_device = parent.current_device
        self.current_accelerator = parent.current_accelerator
        self.japc = parent.japc

        # use this dict to store pyjapc subs data
        self.data_subs = {}

        # init boolean dict to optimize the subsCallback function
        self.firstReceivedSubsPyjapcData = {}

        # set current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # load selector
        self.LoadSelector()

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"].keys())

        # order the property list
        self.property_list.sort()

        # input the command list
        self.command_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["command"].keys())

        # order the command list
        self.command_list.sort()

        # initialize the field dictionary
        self.field_dict = {}

        # set japc selector
        self.japc.setSelector(self.current_selector)

        # when you want to destroy the dialog set this to True
        self._want_to_close = False

        # load the gui, build the widgets and handle the signals
        self.setWindowTitle("DIAMOND BLM SETTINGS ({})".format(self.current_device))
        self.buildCodeWidgets()
        self.bindWidgets()

        # init GET
        self.getFunction(show_message = False)

        # status bar message
        self.app.main_window.statusBar().showMessage("Settings panel of {} loaded successfully!".format(self.current_device), 10*1000)
        self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # event for closing the window in a right way
    def closeEvent(self, evnt):

        # close event
        if self._want_to_close:
            super(SettingsDialogAuto, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setVisible(False)

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # pyuic5 stuff
        self.setObjectName("DIAMOND BLM SETTINGS")
        self.resize(600, 800)
        self.verticalLayout_2 = QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(6, 20, 6, 6)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.frame_properties = QFrame(self)
        self.frame_properties.setFrameShape(QFrame.NoFrame)
        self.frame_properties.setFrameShadow(QFrame.Raised)
        self.frame_properties.setObjectName("frame_properties")
        self.verticalLayout_6 = QVBoxLayout(self.frame_properties)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.scrollArea_properties = QScrollArea(self.frame_properties)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_properties.sizePolicy().hasHeightForWidth())
        self.scrollArea_properties.setSizePolicy(sizePolicy)
        self.scrollArea_properties.setStyleSheet("QScrollArea{\n"
                                                 "    margin-left: 50px;\n"
                                                 "    margin-right: 50px;\n"
                                                 "    background-color: rgb(227, 227, 227);\n"
                                                 "}\n"
                                                 "\n"
                                                 "QScrollBar:vertical{\n"
                                                 "     background-color: white;\n"
                                                 " }\n"
                                                 "\n"
                                                 "CCommandButton{\n"
                                                 "    background-color: rgb(255, 255, 255);\n"
                                                 "    border: 1px solid black;\n"
                                                 "}\n"
                                                 "\n"
                                                 "CCommandButton:hover{\n"
                                                 "    background-color: rgb(230, 230, 230);\n"
                                                 "}\n"
                                                 "\n"
                                                 "CCommandButton:pressed{\n"
                                                 "    background-color: rgb(200, 200, 200);\n"
                                                 "}")
        self.scrollArea_properties.setFrameShadow(QFrame.Plain)
        self.scrollArea_properties.setLineWidth(1)
        self.scrollArea_properties.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_properties.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_properties.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.scrollArea_properties.setWidgetResizable(True)
        self.scrollArea_properties.setAlignment(Qt.AlignCenter)
        self.scrollArea_properties.setObjectName("scrollArea_properties")
        self.scrollingContents_properties = QWidget()
        self.scrollingContents_properties.setGeometry(QRect(0, 50, 454, 575))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollingContents_properties.sizePolicy().hasHeightForWidth())
        self.scrollingContents_properties.setSizePolicy(sizePolicy)
        self.scrollingContents_properties.setStyleSheet("QLabel{\n"
                                                        "    border: 1px solid black;\n"
                                                        "    background-color: rgb(236, 236, 236);\n"
                                                        "}\n"
                                                        "\n"
                                                        "CLabel{\n"
                                                        "    border: 1px solid black;\n"
                                                        "    background-color: rgb(236, 236, 236);\n"
                                                        "}\n"
                                                        "\n"
                                                        "QGroupBox{\n"
                                                        "    background-color: rgb(232, 232, 232);\n"
                                                        "}")
        self.scrollingContents_properties.setObjectName("scrollingContents_properties")
        self.verticalLayout_scrollingContents_properties = QVBoxLayout(self.scrollingContents_properties)
        self.verticalLayout_scrollingContents_properties.setObjectName("verticalLayout_scrollingContents_properties")
        self.scrollArea_properties.setWidget(self.scrollingContents_properties)
        self.verticalLayout_6.addWidget(self.scrollArea_properties)
        self.verticalLayout_2.addWidget(self.frame_properties)
        self.frame_get_set = QFrame(self)
        self.frame_get_set.setFrameShape(QFrame.NoFrame)
        self.frame_get_set.setFrameShadow(QFrame.Plain)
        self.frame_get_set.setObjectName("frame_get_set")
        self.horizontalLayout = QHBoxLayout(self.frame_get_set)
        self.horizontalLayout.setContentsMargins(9, 0, 9, -1)
        self.horizontalLayout.setSpacing(16)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.scrollArea_get_set = QScrollArea(self.frame_get_set)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_get_set.sizePolicy().hasHeightForWidth())
        self.scrollArea_get_set.setSizePolicy(sizePolicy)
        self.scrollArea_get_set.setStyleSheet("background-color: transparent;")
        self.scrollArea_get_set.setFrameShape(QFrame.NoFrame)
        self.scrollArea_get_set.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_get_set.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_get_set.setWidgetResizable(True)
        self.scrollArea_get_set.setAlignment(Qt.AlignCenter)
        self.scrollArea_get_set.setObjectName("scrollArea_get_set")
        self.scrollingContents_get_set = QWidget()
        self.scrollingContents_get_set.setGeometry(QRect(0, 0, 556, 68))
        self.scrollingContents_get_set.setObjectName("scrollingContents_get_set")
        self.horizontalLayout_2 = QHBoxLayout(self.scrollingContents_get_set)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.pushButton_get = QPushButton(self.scrollingContents_get_set)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_get.sizePolicy().hasHeightForWidth())
        self.pushButton_get.setSizePolicy(sizePolicy)
        self.pushButton_get.setMinimumSize(QSize(100, 32))
        font = QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_get.setFont(font)
        self.pushButton_get.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.pushButton_get.setObjectName("pushButton_get")
        self.horizontalLayout_2.addWidget(self.pushButton_get)
        self.pushButton_set = QPushButton(self.scrollingContents_get_set)
        self.pushButton_set.setMinimumSize(QSize(100, 32))
        font = QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_set.setFont(font)
        self.pushButton_set.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.pushButton_set.setObjectName("pushButton_set")
        self.horizontalLayout_2.addWidget(self.pushButton_set)
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.scrollArea_get_set.setWidget(self.scrollingContents_get_set)
        self.horizontalLayout.addWidget(self.scrollArea_get_set)
        self.verticalLayout_2.addWidget(self.frame_get_set)
        self.verticalLayout_2.setStretch(0, 95)
        self.verticalLayout_2.setStretch(1, 5)
        self.pushButton_get.setText("GET")
        self.pushButton_set.setText("SET")

        # initialize widget dicts
        self.groupBoxDict = {}
        self.layoutDict = {}
        self.labelDict = {}
        self.clabelDict = {}
        self.lineEditDict = {}
        self.commandButtonDict = {}
        self.contextFrameDict = {}
        self.tableViewDict = {}
        self.dataTableModelDict = {}
        self.dataModelDict = {}

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # only show the commands when needed
        if SHOW_COMMANDS_IN_SETTINGS:

            # set up the command groupbox first
            self.groupBoxDict["{}".format("Commands")] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format("Commands")].setObjectName("groupBox_{}".format("Commands"))
            self.groupBoxDict["{}".format("Commands")].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format("Commands")].setFlat(True)
            self.groupBoxDict["{}".format("Commands")].setCheckable(False)
            self.groupBoxDict["{}".format("Commands")].setTitle("{}".format("Commands"))
            self.groupBoxDict["{}".format("Commands")].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format("Commands")])

            # layout for the commands
            self.layoutDict["groupBox_{}".format("Commands")] = QGridLayout(self.groupBoxDict["{}".format("Commands")])
            self.layoutDict["groupBox_{}".format("Commands")].setObjectName("layout_groupBox_{}".format("Commands"))

            # add labels and ccommandbuttons to the layout of the command groupbox
            row = 0
            for command in self.command_list:

                # set label (column == 0)
                column = 0
                self.labelDict["{}_{}".format("Commands", command)] = QLabel(self.groupBoxDict["{}".format("Commands")])
                self.labelDict["{}_{}".format("Commands", command)].setObjectName("label_{}_{}".format("Commands", command))
                self.labelDict["{}_{}".format("Commands", command)].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format("Commands", command)].setText("{}".format(command))
                self.labelDict["{}_{}".format("Commands", command)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format("Commands")].addWidget(self.labelDict["{}_{}".format("Commands", command)], row, column, 1, 1)

                # set ccommandbutton (column == 1)
                column = 1
                self.commandButtonDict["{}_{}".format("Commands", command)] = CCommandButton(self.groupBoxDict["{}".format("Commands")])
                self.commandButtonDict["{}_{}".format("Commands", command)].setObjectName("commandButton_{}_{}".format("Commands", command))
                sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(self.commandButtonDict["{}_{}".format("Commands", command)].sizePolicy().hasHeightForWidth())
                self.commandButtonDict["{}_{}".format("Commands", command)].setSizePolicy(sizePolicy)
                self.commandButtonDict["{}_{}".format("Commands", command)].setText("{}".format(" Run"))
                self.commandButtonDict["{}_{}".format("Commands", command)].setIcon(QIcon("icons/command.png"))
                self.commandButtonDict["{}_{}".format("Commands", command)].channel = "{}/{}".format(self.current_device, command)
                self.commandButtonDict["{}_{}".format("Commands", command)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format("Commands")].addWidget(self.commandButtonDict["{}_{}".format("Commands", command)], row, column, 1, 1)

                # get the next field
                row += 1

        # create the group boxes
        for property in self.property_list:

            # init subs pyjapc boolean dict
            self.firstReceivedSubsPyjapcData[property] = False

            # property groupbox
            self.groupBoxDict["{}".format(property)] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format(property)].setObjectName("groupBox_{}".format(property))
            self.groupBoxDict["{}".format(property)].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format(property)].setFlat(True)
            self.groupBoxDict["{}".format(property)].setCheckable(False)
            self.groupBoxDict["{}".format(property)].setTitle("{}".format(property))
            self.groupBoxDict["{}".format(property)].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format(property)])

            # context frame of the groupbox
            self.contextFrameDict["CContextFrame_{}".format(property)] = CContextFrame(self.groupBoxDict["{}".format(property)])
            self.contextFrameDict["CContextFrame_{}".format(property)].setObjectName("CContextFrame_{}".format(property))
            self.contextFrameDict["CContextFrame_{}".format(property)].inheritSelector = False
            self.contextFrameDict["CContextFrame_{}".format(property)].selector = self.current_selector

            # layout of the context frame (0 margin)
            self.layoutDict["CContextFrame_{}".format(property)] = QVBoxLayout(self.groupBoxDict["{}".format(property)])
            self.layoutDict["CContextFrame_{}".format(property)].setObjectName("CContextFrame_{}".format(property))
            self.layoutDict["CContextFrame_{}".format(property)].setContentsMargins(0, 0, 0, 0)
            self.layoutDict["CContextFrame_{}".format(property)].addWidget(self.contextFrameDict["CContextFrame_{}".format(property)])

            # property layout
            self.layoutDict["groupBox_{}".format(property)] = QGridLayout(self.contextFrameDict["CContextFrame_{}".format(property)])
            self.layoutDict["groupBox_{}".format(property)].setObjectName("layout_groupBox_{}".format(property))

            # retrieve the field setting names
            self.field_dict["{}".format(property)] = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["scalar"].keys())
            self.field_dict["{}".format(property)].sort()

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # in case the property is multiplexed, create a subscription kind of channel (i.e. use CLabel)
            if is_multiplexed == "True":

                # use an empty selector for LHC devices
                if self.current_accelerator == "LHC":
                    selectorOverride = ""
                # use SPS.USER.ALL for SPS devices
                elif self.current_accelerator == "SPS":
                    selectorOverride = "SPS.USER.ALL"
                # use an empty selector for the others
                else:
                    selectorOverride = ""

                # create subs
                self.japc.subscribeParam("{}/{}".format(self.current_device, property), onValueReceived=self.subsCallback, onException=self.onException, timingSelectorOverride=selectorOverride)
                self.japc.startSubscriptions()

                # create table
                self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
                self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                                 "    background-color: rgb(243, 243, 243);\n"
                                                                 "    margin-top: 0;\n"
                                                                 "}")
                self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
                self.tableViewDict[property].setFrameShadow(QFrame.Plain)
                self.tableViewDict[property].setDragEnabled(False)
                self.tableViewDict[property].setAlternatingRowColors(True)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].setShowGrid(True)
                self.tableViewDict[property].setGridStyle(Qt.SolidLine)
                self.tableViewDict[property].setObjectName("tableView_general_information")
                self.tableViewDict[property].horizontalHeader().setVisible(False)
                self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
                self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
                self.tableViewDict[property].verticalHeader().setVisible(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
                self.tableViewDict[property].verticalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
                self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].setEditTriggers(QAbstractItemView.NoEditTriggers)
                self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
                self.tableViewDict[property].horizontalHeader().setStyleSheet(
                    "font-weight:bold; background-color: rgb(210, 210, 210);")
                self.tableViewDict[property].show()
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

            # in case the property is not multiplexed, create a GET kind of channel (i.e. use QLabel)
            else:

                # create table
                self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
                self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                           "    background-color: rgb(243, 243, 243);\n"
                                                           "    margin-top: 0;\n"
                                                           "}")
                self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
                self.tableViewDict[property].setFrameShadow(QFrame.Plain)
                self.tableViewDict[property].setDragEnabled(False)
                self.tableViewDict[property].setAlternatingRowColors(True)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].setShowGrid(True)
                self.tableViewDict[property].setGridStyle(Qt.SolidLine)
                self.tableViewDict[property].setObjectName("tableView_general_information")
                self.tableViewDict[property].horizontalHeader().setVisible(False)
                self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
                self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
                self.tableViewDict[property].verticalHeader().setVisible(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
                self.tableViewDict[property].verticalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
                self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].setEditTriggers(QAbstractItemView.NoEditTriggers)
                self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
                self.tableViewDict[property].horizontalHeader().setStyleSheet(
                    "font-weight:bold; background-color: rgb(210, 210, 210);")
                self.tableViewDict[property].show()
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

        # make the scroll bar of the get and set panel invisible
        sp_scroll_area_get_set = self.scrollArea_get_set.verticalScrollBar().sizePolicy()
        sp_scroll_area_get_set.setRetainSizeWhenHidden(True)
        self.scrollArea_get_set.verticalScrollBar().setSizePolicy(sp_scroll_area_get_set)
        self.scrollArea_get_set.verticalScrollBar().hide()

        return

    #----------------------------------------------#

    # function to receive pyjapc subs data
    def subsCallback(self, parameterName, dictValues, verbose = False):

        # get property name
        prop_name = parameterName.split("/")[1]

        # check that the values are different with respect to the previous iteration
        if self.firstReceivedSubsPyjapcData[prop_name]:
            if self.data_subs[prop_name] == dictValues:
                return

        # store the data
        self.data_subs[prop_name] = dictValues

        # update boolean
        self.firstReceivedSubsPyjapcData[prop_name] = True

        # print
        if verbose:
            print("{} - Received {} values...".format(UI_FILENAME, prop_name))

        return

    #----------------------------------------------#

    # function that handles pyjapc exceptions
    def onException(self, parameterName, description, exception, verbose = True):

        # print
        if verbose:
            print("{} - {}".format(UI_FILENAME, exception))

        # nothing
        pass

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # getters
        self.pushButton_get.clicked.connect(lambda: self.getFunction(show_message = True))

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        # selector signal
        self.app.main_window.window_context.selectorChanged.connect(self.selectorWasChanged)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        return

    #----------------------------------------------#

    # function that handles japc and UI stuff when rbac is disconnected
    def rbacLogoutSucceeded(self):

        # print message
        print("{} - RBAC logout succeeded...".format(UI_FILENAME))

        # end pyjapc rbac connection
        self.japc.rbacLogout()

        return

    #----------------------------------------------#

    # this function gets activated whenever RBAC logins successfully
    def rbacLoginSucceeded(self):

        # print message
        print("{} - RBAC login succeeded...".format(UI_FILENAME))

        # save the token into the environmental variable so that we can read it with pyjapc
        os.environ["RBAC_TOKEN_SERIALIZED"] = self.app._rbac.serialized_token

        # now that we have a token try to login with japc too
        self.japc.rbacLogin(readEnv=True)

        return

    #----------------------------------------------#

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""
        print("{} - New selector is: {}".format(UI_FILENAME, self.current_selector))

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that retrieves and displays the values of the fields
    def getFunction(self, show_message = False):

        # print the GET action
        print("{} - Button GET pressed".format(UI_FILENAME))

        # create a field dictionary to see which fields changed
        self.field_values_macro_dict = {}

        # iterate over all properties
        for property in self.property_list:

            # init data list
            self.dataModelDict[property] = []

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # in case the property is multiplexed, the connection is via subscription so a GET is useless (i.e. skip it)
            if is_multiplexed == "True":

                # get the field values from the label text
                self.field_values_macro_dict["{}".format(property)] = {}

                # iterate over all fields
                for field in self.field_dict["{}".format(property)]:

                    # fill the dict and set text
                    try:
                        self.field_values_macro_dict["{}".format(property)][field] = self.data_subs[property][field]
                        self.dataModelDict[property].append([str(field), str(self.data_subs[property][field])])
                    except:
                        self.dataModelDict[property].append([str(field), "-"])

                # update model
                self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[])
                self.tableViewDict[property].setModel(self.dataTableModelDict[property])
                self.tableViewDict[property].update()

                # update groupbox size in function of the number of rows
                self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

                # skip the property
                continue

            # in case the property is not multiplexed, a GET is required
            else:

                # get the new field values via pyjapc and add them to the field_values_macro_dict
                field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride="")

                # add field values to the macro dict
                self.field_values_macro_dict["{}".format(property)] = field_values

                # iterate over all fields
                for field in self.field_dict["{}".format(property)]:

                    # set text
                    self.dataModelDict[property].append([str(field), str(field_values[field])])

                # update model
                self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[])
                self.tableViewDict[property].setModel(self.dataTableModelDict[property])
                self.tableViewDict[property].update()

                # update groupbox size in function of the number of rows
                self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

        # status bar message
        if show_message:
            self.app.main_window.statusBar().showMessage("Command GET ran successfully!", 3*1000)
            self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET#1 pressed".format(UI_FILENAME))

        # get before set
        self.getFunction(show_message = False)

        # open the dialog
        self.dialog_three_column_set = DialogThreeColumnSet(parent = self)
        self.dialog_three_column_set.setModal(True)
        self.dialog_three_column_set.show()
        self.dialog_three_column_set.nturns_changed.connect(self.notifyParent)

        return

    #----------------------------------------------#

    # function that emits a signal to its parent
    def notifyParent(self):

        # emit the signal if there has been changes to the nturns
        self.nturns_changed.emit(True)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadSelector(self):

        # read current device
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt"), "r") as f:
                self.current_selector = f.read()

        return

    #----------------------------------------------#


########################################################
########################################################

class GetFieldInfoThreadWorker1ShowUp(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(int, list, dict, bool)
    iterated = pyqtSignal()

    #----------------------------------------------#

    # init function
    def __init__(self, r, device_list, property_list, field_list, working_devices, current_accelerator, pyccda_dictionary, japc, cern):

        # inherit from QObject
        QObject.__init__(self)

        # declare attributes
        self.r = r
        self.device_list = device_list
        self.property_list = property_list
        self.field_list = field_list
        self.working_devices = working_devices
        self.current_accelerator = current_accelerator
        self.pyccda_dictionary = pyccda_dictionary
        self.japc = japc
        self.cern = cern

        return

    #----------------------------------------------#

    # start function
    def start(self):

        # sleep the thread a bit in a random fashion
        QThread.msleep(random.randint(250,750))

        # get row
        r = self.r

        # boolean to skip general information
        is_general_information = False

        # init row list
        row_list = []

        # init error dict for that row
        row_error_dict = {}

        # operate as a field
        if r < len(self.field_list):

            # declare the field
            field = self.field_list[r]

            # append first element which is the field / mode
            row_list.append(str(field))
            row_error_dict[0] = ""

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
                        row_error_dict[c+1] = ""
                    except:
                        pass

                # if the device IS not working
                else:

                    # update the list with null information
                    row_list.append("-")
                    row_error_dict[c+1] = "NOT_WORKING_DEVICE"

                # send signal to update the counter of the progress dialog
                self.iterated.emit()

        # operate as a mode
        else:

            # declare the property
            property = self.property_list[r-len(self.field_list)]

            # skip general information property
            if property == "GeneralInformation":

                # update boolean
                is_general_information = True

                # emit the signal with all the data
                self.processed.emit(r, row_list, row_error_dict, is_general_information)

                return

            # append first element which is the field / mode
            row_list.append(str(property))
            row_error_dict[0] = ""

            # iterate over devices
            for c, device in enumerate(self.device_list):

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
                            nturns = 0
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
                                row_error_dict[c + 1] = ""

                            # if buffers are empty show a custom error
                            else:

                                # BUFFERS_ARE_EMPTY
                                row_list.append("BUFFERS_ARE_EMPTY")
                                row_error_dict[c + 1] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

                        # for the others we should care about timestamps
                        else:

                            # show a custom error if nturns is 0
                            if nturns == 0:

                                # NTURNS_IS_ZERO
                                row_list.append("NTURNS_IS_ZERO")
                                row_error_dict[c + 1] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

                            # normal procedure
                            else:

                                # compare timestamps
                                if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):
                                    row_list.append("MODE_BEING_ANALYZED")
                                    row_error_dict[c + 1] = "custom.message.error: MODE_BEING_ANALYZED: The mode {} is still being analyzed in a different thread. Wait a few seconds until a decision about its availability is made.".format(property)
                                else:
                                    row_list.append("TIMESTAMP_TOO_OLD")
                                    row_error_dict[c + 1] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

                    # this exception is usually NO_DATA_AVAILABLE_FOR_USER (happens when it is not initialized yet)
                    except self.cern.japc.core.ParameterException as xcp:

                        # NO_DATA_AVAILABLE_FOR_USER
                        row_list.append(str(xcp.getMessage()).split(":")[0])
                        row_error_dict[c + 1] = str(xcp)

                # if the device IS not working
                else:

                    # update the list with null information
                    row_list.append("-")
                    row_error_dict[c + 1] = "NOT_WORKING_DEVICE"

                # send signal to update the counter of the progress dialog
                self.iterated.emit()

        # emit the signal with all the data
        self.processed.emit(r, row_list, row_error_dict, is_general_information)

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # stop and emit the finish signal
        self.finished.emit()

        return

    #----------------------------------------------#

########################################################
########################################################

class workingModesThreadWorkerSummary(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(dict, dict, str)

    #----------------------------------------------#

    # init function
    def __init__(self, current_device, acc_device_list, current_accelerator, japc, property_list, cern, pyccda_dictionary):

        # inherit from QObject
        QObject.__init__(self)

        # declare timers
        self.timer_watchdog_AcquisitionHistogram = QTimer(self)
        self.timer_watchdog_AcquisitionIntegral = QTimer(self)
        # self.timer_watchdog_AcquisitionIntegralDist = QTimer(self)
        # self.timer_watchdog_AcquisitionRawDist = QTimer(self)
        self.timer_watchdog_AcquisitionTurnLoss = QTimer(self)
        self.timer_watchdog_Capture = QTimer(self)

        # declare attributes
        self.current_device = current_device
        self.device_list = acc_device_list
        self.current_accelerator = current_accelerator
        self.japc = japc
        self.property_list = property_list
        self.cern = cern
        self.exit_boolean = False
        self.pyccda_dictionary = pyccda_dictionary

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # update stop variable
        self.exit_boolean = True

        # stop timers
        # self.timer_watchdog_AcquisitionHistogram.stop()
        # self.timer_watchdog_AcquisitionIntegral.stop()
        # self.timer_watchdog_AcquisitionIntegralDist.stop()
        # self.timer_watchdog_AcquisitionRawDist.stop()
        # self.timer_watchdog_AcquisitionTurnLoss.stop()
        # self.timer_watchdog_Capture.stop()
        # del self.timer_watchdog_AcquisitionHistogram
        # del self.timer_watchdog_AcquisitionIntegral
        # del self.timer_watchdog_AcquisitionIntegralDist
        # del self.timer_watchdog_AcquisitionRawDist
        # del self.timer_watchdog_AcquisitionTurnLoss
        # del self.timer_watchdog_Capture

        # emit the finish signal
        self.finished.emit()

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionHistogram(self):

        # declare the property
        property = "AcquisitionHistogram"

        # init check
        if self.current_device not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY.keys():
            return
        if property not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device].keys():
            return

        # get timestamps
        get_ts = LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device][property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionHistogram
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionHistogram

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = "NTURNS_IS_ZERO"
            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = "{}".format(str(get_ts))
                self.errors[property] = ""

            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = "TIMESTAMP_TOO_OLD"
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors, self.current_device)

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionIntegral(self):

        # declare the property
        property = "AcquisitionIntegral"

        # init check
        if self.current_device not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY.keys():
            return
        if property not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device].keys():
            return

        # get timestamps
        get_ts = LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device][property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionIntegral
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionIntegral

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = "NTURNS_IS_ZERO"
            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
            self.modules_data["AcquisitionIntegralDist"] = "NTURNS_IS_ZERO"
            self.errors["AcquisitionIntegralDist"] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
            self.modules_data["AcquisitionRawDist"] = "NTURNS_IS_ZERO"
            self.errors["AcquisitionRawDist"] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = "{}".format(str(get_ts))
                self.errors[property] = ""
                self.modules_data["AcquisitionIntegralDist"] = "{}".format(str(get_ts))
                self.errors["AcquisitionIntegralDist"] = ""
                self.modules_data["AcquisitionRawDist"] = "{}".format(str(get_ts))
                self.errors["AcquisitionRawDist"] = ""

            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = "TIMESTAMP_TOO_OLD"
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
                self.modules_data["AcquisitionIntegralDist"] = "TIMESTAMP_TOO_OLD"
                self.errors["AcquisitionIntegralDist"] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
                self.modules_data["AcquisitionRawDist"] = "TIMESTAMP_TOO_OLD"
                self.errors["AcquisitionRawDist"] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors, self.current_device)

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionTurnLoss(self):

        # declare the property
        property = "AcquisitionTurnLoss"

        # init check
        if self.current_device not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY.keys():
            return
        if property not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device].keys():
            return

        # get timestamps
        get_ts = LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device][property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionTurnLoss
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionTurnLoss

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = "NTURNS_IS_ZERO"
            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = "{}".format(str(get_ts))
                self.errors[property] = ""

            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = "TIMESTAMP_TOO_OLD"
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors, self.current_device)

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsCapture(self):

        # declare the property
        property = "Capture"

        # init check
        if self.current_device not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY.keys():
            return
        if property not in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device].keys():
            return

        # get timestamps
        get_ts = LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[self.current_device][property]
        current_ts = datetime.now(timezone.utc)

        # if the buffer is not empty
        if DATA_SUBS_SUMMARY[self.current_device][property]["rawBuf0"].size > 0:

            # if the try did not give an error then it is working
            self.modules_data[property] = "{}".format(str(get_ts))
            self.errors[property] = ""

        # if buffers are empty show a custom error
        else:

            # BUFFERS_ARE_EMPTY
            self.modules_data[property] = "BUFFERS_ARE_EMPTY"
            self.errors[property] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

        # emit the signal
        self.processed.emit(self.modules_data, self.errors, self.current_device)

        return

    #----------------------------------------------#

    # processing function
    def start(self, verbose = False):

        # print thread address
        if verbose:
            print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))

        # init dicts for the table
        self.modules_data = {}
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

        # sleep a little bit to give some time to the subs callback
        QThread.msleep(500)

        # ACQUISITION HISTOGRAM

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossHistogramSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionHistogram = nturns
            self.turn_time_in_seconds_AcquisitionHistogram = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionHistogram != 0:
            self.timer_watchdog_AcquisitionHistogram.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionHistogram.timeout.connect(self.compareTimestampsAcquisitionHistogram)
            self.timer_watchdog_AcquisitionHistogram.start()

        # ACQUISITION INTEGRAL

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossIntegralSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionIntegral = nturns
            self.turn_time_in_seconds_AcquisitionIntegral = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionIntegral != 0:
            self.timer_watchdog_AcquisitionIntegral.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionIntegral.timeout.connect(self.compareTimestampsAcquisitionIntegral)

        # ACQUISITION TURN LOSS

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["TurnLossMeasurementSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "TurnLossMeasurementSetting", "turnTrackCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionTurnLoss = nturns
            self.turn_time_in_seconds_AcquisitionTurnLoss = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionTurnLoss != 0:
            self.timer_watchdog_AcquisitionTurnLoss.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionTurnLoss.timeout.connect(self.compareTimestampsAcquisitionTurnLoss)

        # CAPTURE

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        self.timer_watchdog_Capture.setInterval(2 * 1000)
        self.timer_watchdog_Capture.timeout.connect(self.compareTimestampsCapture)

        # ALL TIMERS

        # start all timers
        if self.nturns_AcquisitionHistogram:
            self.timer_watchdog_AcquisitionHistogram.start()
        if self.nturns_AcquisitionIntegral:
            self.timer_watchdog_AcquisitionIntegral.start()
        if self.nturns_AcquisitionTurnLoss:
            self.timer_watchdog_AcquisitionTurnLoss.start()
        self.timer_watchdog_Capture.start()

        return

    #----------------------------------------------#

########################################################
########################################################

class workingModesThreadWorkerPreview(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(dict, dict)

    #----------------------------------------------#

    # init function
    def __init__(self, current_device, current_accelerator, japc, property_list, cern, pyccda_dictionary):

        # inherit from QObject
        QObject.__init__(self)

        # declare timers
        self.timer_watchdog_AcquisitionHistogram = QTimer(self)
        self.timer_watchdog_AcquisitionIntegral = QTimer(self)
        # self.timer_watchdog_AcquisitionIntegralDist = QTimer(self)
        # self.timer_watchdog_AcquisitionRawDist = QTimer(self)
        self.timer_watchdog_AcquisitionTurnLoss = QTimer(self)
        self.timer_watchdog_Capture = QTimer(self)

        # declare attributes
        self.current_device = current_device
        self.current_accelerator = current_accelerator
        self.japc = japc
        self.property_list = property_list
        self.cern = cern
        self.exit_boolean = False
        self.pyccda_dictionary = pyccda_dictionary

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # update stop variable
        self.exit_boolean = True

        # stop timers
        # self.timer_watchdog_AcquisitionHistogram.stop()
        # self.timer_watchdog_AcquisitionIntegral.stop()
        # self.timer_watchdog_AcquisitionIntegralDist.stop()
        # self.timer_watchdog_AcquisitionRawDist.stop()
        # self.timer_watchdog_AcquisitionTurnLoss.stop()
        # self.timer_watchdog_Capture.stop()
        # del self.timer_watchdog_AcquisitionHistogram
        # del self.timer_watchdog_AcquisitionIntegral
        # del self.timer_watchdog_AcquisitionIntegralDist
        # del self.timer_watchdog_AcquisitionRawDist
        # del self.timer_watchdog_AcquisitionTurnLoss
        # del self.timer_watchdog_Capture

        # emit the finish signal
        self.finished.emit()

        return

    #----------------------------------------------#

    # function that handles pyjapc exceptions
    def onException(self, parameterName, description, exception, verbose = False):

        # print
        if verbose:
            print("{} - Exception: {}".format(UI_FILENAME, exception))

        # nothing
        pass

        return

    #----------------------------------------------#

    # function to receive pyjapc subs data
    def subsCallback(self, parameterName, dictValues, headerInfo, verbose = False):

        # get property name
        prop_name = parameterName.split("/")[1]

        # ignore GeneralInformation
        if prop_name == "GeneralInformation":
            return

        # store the data
        self.data_subs[prop_name] = dictValues

        # store last timestamp of the callback
        self.LAST_TIMESTAMP_SUB_CALLBACK[prop_name] = headerInfo["acqStamp"]

        # print
        if verbose:
            print("{} - Received {} values for {}...".format(UI_FILENAME, prop_name, self.current_device))

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionHistogram(self):

        # declare the property
        property = "AcquisitionHistogram"

        # init check
        if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
            return

        # get timestamps
        get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionHistogram
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionHistogram

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                self.errors[property] = "-"

            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = [property, "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors)

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionIntegral(self):

        # declare the property
        property = "AcquisitionIntegral"

        # init check
        if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
            return

        # get timestamps
        get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionIntegral
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionIntegral

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
            self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
            self.modules_data["AcquisitionIntegralDist"] = ["AcquisitionIntegralDist", "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
            self.errors["AcquisitionIntegralDist"] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
            self.modules_data["AcquisitionRawDist"] = ["AcquisitionRawDist", "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
            self.errors["AcquisitionRawDist"] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                self.errors[property] = "-"
                self.modules_data["AcquisitionIntegralDist"] = ["AcquisitionIntegralDist", "Yes", "-", "{}".format(str(get_ts))]
                self.errors["AcquisitionIntegralDist"] = "-"
                self.modules_data["AcquisitionRawDist"] = ["AcquisitionRawDist", "Yes", "-", "{}".format(str(get_ts))]
                self.errors["AcquisitionRawDist"] = "-"


            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = [property, "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
                self.modules_data["AcquisitionIntegralDist"] = ["AcquisitionIntegralDist", "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                self.errors["AcquisitionIntegralDist"] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
                self.modules_data["AcquisitionRawDist"] = ["AcquisitionRawDist", "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                self.errors["AcquisitionRawDist"] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors)

        return

    #----------------------------------------------#

    # # function that compares the timestamps and determines if modes are running or not
    # def compareTimestampsAcquisitionIntegralDist(self):
    #
    #     # declare the property
    #     property = "AcquisitionIntegralDist"
    #
    #     # init check
    #     if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
    #         return
    #
    #     # get timestamps
    #     get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
    #     current_ts = datetime.now(timezone.utc)
    #
    #     # get nturns
    #     nturns = self.nturns_AcquisitionIntegralDist
    #     turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionIntegralDist
    #
    #     # show a custom error if nturns is 0
    #     if nturns == 0:
    #
    #         # NTURNS_IS_ZERO
    #         self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
    #         self.errors[
    #             property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
    #
    #     # normal procedure
    #     else:
    #
    #         # compare timestamps
    #         if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):
    #
    #             # WORKING MODE
    #             self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
    #             self.errors[property] = "-"
    #
    #         # ts is too old
    #         else:
    #
    #             # TS_TOO_OLD
    #             self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
    #             self.errors[property] = "custom.message.error: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
    #
    #     return

    #----------------------------------------------#

    # # function that compares the timestamps and determines if modes are running or not
    # def compareTimestampsAcquisitionRawDist(self):
    #
    #     # declare the property
    #     property = "AcquisitionRawDist"
    #
    #     # init check
    #     if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
    #         return
    #
    #     # get timestamps
    #     get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
    #     current_ts = datetime.now(timezone.utc)
    #
    #     # get nturns
    #     nturns = self.nturns_AcquisitionRawDist
    #     turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionRawDist
    #
    #     # show a custom error if nturns is 0
    #     if nturns == 0:
    #
    #         # NTURNS_IS_ZERO
    #         self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
    #         self.errors[
    #             property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
    #
    #     # normal procedure
    #     else:
    #
    #         # compare timestamps
    #         if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):
    #
    #             # WORKING MODE
    #             self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
    #             self.errors[property] = "-"
    #
    #         # ts is too old
    #         else:
    #
    #             # TS_TOO_OLD
    #             self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
    #             self.errors[property] = "custom.message.error: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
    #
    #     return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsAcquisitionTurnLoss(self):

        # declare the property
        property = "AcquisitionTurnLoss"

        # init check
        if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
            return

        # get timestamps
        get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
        current_ts = datetime.now(timezone.utc)

        # get nturns
        nturns = self.nturns_AcquisitionTurnLoss
        turn_time_in_seconds = self.turn_time_in_seconds_AcquisitionTurnLoss

        # show a custom error if nturns is 0
        if nturns == 0:

            # NTURNS_IS_ZERO
            self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
            self.errors[
                property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

        # normal procedure
        else:

            # compare timestamps
            if current_ts - get_ts < timedelta(seconds=turn_time_in_seconds * ACCEPTANCE_FACTOR):

                # WORKING MODE
                self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                self.errors[property] = "-"

            # ts is too old
            else:

                # TS_TOO_OLD
                self.modules_data[property] = [property, "No", "TIMESTAMP_TOO_OLD", "{}".format(str(get_ts))]
                self.errors[property] = "custom.message.error: TIMESTAMP_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)

        # emit the signal
        self.processed.emit(self.modules_data, self.errors)

        return

    #----------------------------------------------#

    # function that compares the timestamps and determines if modes are running or not
    def compareTimestampsCapture(self):

        # declare the property
        property = "Capture"

        # init check
        if property not in self.LAST_TIMESTAMP_SUB_CALLBACK.keys():
            return

        # get timestamps
        get_ts = self.LAST_TIMESTAMP_SUB_CALLBACK[property]
        current_ts = datetime.now(timezone.utc)

        # if the buffer is not empty
        if self.data_subs[property]["rawBuf0"].size > 0:

            # if the try did not give an error then it is working
            self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
            self.errors[property] = "-"

        # if buffers are empty show a custom error
        else:

            # BUFFERS_ARE_EMPTY
            self.modules_data[property] = [property, "No", "BUFFERS_ARE_EMPTY", "{}".format(str(get_ts))]
            self.errors[property] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

        # emit the signal
        self.processed.emit(self.modules_data, self.errors)

        return

    #----------------------------------------------#

    # processing function
    def start(self, verbose = False):

        # print thread address
        if verbose:
            print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))

        # init dicts for the table
        self.modules_data = {}
        self.errors = {}

        # use this to store the timestamps of the callback
        self.LAST_TIMESTAMP_SUB_CALLBACK = {}

        # use this dict to store pyjapc subs data
        self.data_subs = {}

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

        # create subs
        for property in self.property_list:
            if property != "GeneralInformation":
                self.japc.subscribeParam("{}/{}".format(self.current_device, property), onValueReceived=self.subsCallback, onException=self.onException, timingSelectorOverride=selectorOverride, getHeader=True)
                self.japc.startSubscriptions()

        # sleep a little bit to give some time to the subs callback
        QThread.msleep(500)

        # ACQUISITION HISTOGRAM

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossHistogramSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionHistogram = nturns
            self.turn_time_in_seconds_AcquisitionHistogram = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionHistogram != 0:
            self.timer_watchdog_AcquisitionHistogram.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionHistogram.timeout.connect(self.compareTimestampsAcquisitionHistogram)
            self.timer_watchdog_AcquisitionHistogram.start()

        # ACQUISITION INTEGRAL

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossIntegralSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionIntegral = nturns
            self.turn_time_in_seconds_AcquisitionIntegral = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionIntegral != 0:
            self.timer_watchdog_AcquisitionIntegral.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionIntegral.timeout.connect(self.compareTimestampsAcquisitionIntegral)

        # # ACQUISITION INTEGRAL DIST
        #
        # # get nturns
        # try:
        #     is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossIntegralSetting"]["mux"]
        #     if is_multiplexed == "False":
        #         selectorOverride = ""
        #     nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
        #     if self.current_accelerator == "LHC":
        #         turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
        #     elif self.current_accelerator == "SPS":
        #         turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
        #     else:
        #         turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
        #     self.nturns_AcquisitionIntegralDist = nturns
        #     self.turn_time_in_seconds_AcquisitionIntegralDist = turn_time_in_seconds
        # except Exception as xcp:
        #     print(xcp)
        #     pass
        #
        # # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        # if self.nturns_AcquisitionIntegralDist != 0:
        #     self.timer_watchdog_AcquisitionIntegralDist.setInterval(turn_time_in_seconds * 1000)
        #     self.timer_watchdog_AcquisitionIntegralDist.timeout.connect(self.compareTimestampsAcquisitionIntegralDist)

        # # ACQUISITION RAW DIST
        #
        # # get nturns
        # try:
        #     is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["BeamLossIntegralSetting"]["mux"]
        #     if is_multiplexed == "False":
        #         selectorOverride = ""
        #     nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
        #     if self.current_accelerator == "LHC":
        #         turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
        #     elif self.current_accelerator == "SPS":
        #         turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
        #     else:
        #         turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
        #     self.nturns_AcquisitionRawDist = nturns
        #     self.turn_time_in_seconds_AcquisitionRawDist = turn_time_in_seconds
        # except Exception as xcp:
        #     print(xcp)
        #     pass
        #
        # # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        # if self.nturns_AcquisitionRawDist != 0:
        #     self.timer_watchdog_AcquisitionRawDist.setInterval(turn_time_in_seconds * 1000)
        #     self.timer_watchdog_AcquisitionRawDist.timeout.connect(self.compareTimestampsAcquisitionRawDist)

        # ACQUISITION TURN LOSS

        # get nturns
        try:
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"]["TurnLossMeasurementSetting"]["mux"]
            if is_multiplexed == "False":
                selectorOverride = ""
            nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "TurnLossMeasurementSetting", "turnTrackCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            if self.current_accelerator == "LHC":
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            elif self.current_accelerator == "SPS":
                turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
            else:
                turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
            self.nturns_AcquisitionTurnLoss = nturns
            self.turn_time_in_seconds_AcquisitionTurnLoss = turn_time_in_seconds
        except Exception as xcp:
            print(xcp)
            pass

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        if self.nturns_AcquisitionTurnLoss != 0:
            self.timer_watchdog_AcquisitionTurnLoss.setInterval(turn_time_in_seconds * 1000)
            self.timer_watchdog_AcquisitionTurnLoss.timeout.connect(self.compareTimestampsAcquisitionTurnLoss)

        # CAPTURE

        # init a timer that runs every Tnew * NumPeriods (number of periods in between checks)
        self.timer_watchdog_Capture.setInterval(2 * 1000)
        self.timer_watchdog_Capture.timeout.connect(self.compareTimestampsCapture)

        # ALL TIMERS

        # start all timers
        if self.nturns_AcquisitionHistogram:
            self.timer_watchdog_AcquisitionHistogram.start()
        if self.nturns_AcquisitionIntegral:
            self.timer_watchdog_AcquisitionIntegral.start()
        # if self.nturns_AcquisitionIntegralDist:
        #     self.timer_watchdog_AcquisitionIntegralDist.start()
        # if self.nturns_AcquisitionRawDist:
        #     self.timer_watchdog_AcquisitionRawDist.start()
        if self.nturns_AcquisitionTurnLoss:
            self.timer_watchdog_AcquisitionTurnLoss.start()
        self.timer_watchdog_Capture.start()

        return

    #----------------------------------------------#

# class workingModesThreadWorkerPreview(QObject):
#
#     #----------------------------------------------#
#
#     # signals
#     finished = pyqtSignal()
#     processed = pyqtSignal(dict, dict)
#
#     #----------------------------------------------#
#
#     # init function
#     def __init__(self, current_device, current_accelerator, japc, property_list, cern):
#
#         # inherit from QObject
#         QObject.__init__(self)
#
#         # declare attributes
#         self.current_device = current_device
#         self.current_accelerator = current_accelerator
#         self.japc = japc
#         self.property_list = property_list
#         self.cern = cern
#         self.exit_boolean = False
#
#         return
#
#     #----------------------------------------------#
#
#     # stop function
#     def stop(self):
#
#         # update stop variable
#         self.exit_boolean = True
#
#         # emit the finish signal
#         self.finished.emit()
#
#         return
#
#     #----------------------------------------------#
#
#     # processing function
#     def start(self, verbose = False):
#
#         # print thread address
#         if verbose:
#             print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))
#
#         # init the data model dict for the working modules table
#         self.modules_data = {}
#
#         # store full errors
#         self.errors = {}
#
#         # selectorOverride for the working modules table has to be a specific selector
#         # use an empty selector for LHC devices
#         if self.current_accelerator == "LHC":
#             selectorOverride = ""
#         # use SPS.USER.ALL for SPS devices
#         elif self.current_accelerator == "SPS":
#             selectorOverride = "SPS.USER.SFTPRO1"
#         # use an empty selector for the others
#         else:
#             selectorOverride = ""
#
#         # counter for the while
#         counter_property = 0
#
#         # continuously analyze the modes until stop is called
#         while not self.exit_boolean:
#
#             # property declaration
#             if counter_property == len(self.property_list):
#                 counter_property = 0
#             property = self.property_list[counter_property]
#
#             # skip general information property
#             if property == "GeneralInformation":
#                 counter_property += 1
#                 continue
#
#             # get nturns
#             try:
#
#                 # in the LHC: 1 turn = 89 microseconds (updates each 1 second if nturn = 11245)
#                 # in the SPS: 1 turn = 23.0543 microseconds (updates each 0.1 second if nturn = 4338)
#                 if property == "AcquisitionHistogram":
#                     nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossHistogramSetting", "blmNTurn"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
#                 elif property == "AcquisitionIntegral" or property == "AcquisitionIntegralDist" or property == "AcquisitionRawDist":
#                     nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "BeamLossIntegralSetting", "turnAvgCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
#                 elif property == "AcquisitionTurnLoss":
#                     nturns = float(self.japc.getParam("{}/{}#{}".format(self.current_device, "TurnLossMeasurementSetting", "turnTrackCnt"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
#                 elif property == "Capture":
#                     pass
#                 else:
#                     print("{} - Error (unknown property {})".format(UI_FILENAME, property))
#                 if self.current_accelerator == "LHC":
#                     turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
#                 elif self.current_accelerator == "SPS":
#                     turn_time_in_seconds = nturns * TURN_TIME_SPS / 1000000
#                 else:
#                     turn_time_in_seconds = nturns * TURN_TIME_LHC / 1000000
#
#             # if this does not work, then nothing should be working (NO_DATA_AVAILABLE_FOR_USER likely)
#             except:
#
#                 # pass
#                 pass
#
#             # do a GET request via japc
#             try:
#
#                 # get the fields
#                 field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)
#
#                 # get timestamps
#                 get_ts = field_values[1]["acqStamp"]
#                 current_ts = datetime.now(timezone.utc)
#
#                 # for the capture do not care about timestamps
#                 if property == "Capture":
#
#                     # if the buffer is not empty
#                     if field_values[0]["rawBuf0"].size > 0:
#
#                         # if the try did not give an error then it is working
#                         self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
#                         self.errors[property] = "-"
#
#                     # if buffers are empty show a custom error
#                     else:
#
#                         # BUFFERS_ARE_EMPTY
#                         self.modules_data[property] = [property, "No", "BUFFERS_ARE_EMPTY", "{}".format(str(get_ts))]
#                         self.errors[property] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."
#
#                 # for the others we should care about timestamps
#                 else:
#
#                     # show a custom error if nturns is 0
#                     if nturns == 0:
#
#                         # NTURNS_IS_ZERO
#                         self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
#                         self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."
#
#                     # normal procedure
#                     else:
#
#                         # compare timestamps
#                         if current_ts - get_ts < timedelta(seconds = turn_time_in_seconds * ACCEPTANCE_FACTOR):
#
#                             # sleep a little bit
#                             QThread.msleep(int(turn_time_in_seconds*ACCEPTANCE_FACTOR*1000))
#
#                             # do a second GET
#                             field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)
#                             get_ts = field_values[1]["acqStamp"]
#                             current_ts = datetime.now(timezone.utc)
#
#                             # compare timestamps again
#                             if current_ts - get_ts < timedelta(seconds = turn_time_in_seconds * ACCEPTANCE_FACTOR):
#
#                                 # WORKING MODE
#                                 self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
#                                 self.errors[property] = "-"
#
#                             # 2nd check still too old
#                             else:
#
#                                 # TS_TOO_OLD
#                                 self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
#                                 self.errors[property] = "custom.message.error.2nd.check: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
#
#                         # 1st check too old
#                         else:
#
#                             # TS_TOO_OLD
#                             self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
#                             self.errors[property] = "custom.message.error.1st.check: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds * ACCEPTANCE_FACTOR, current_ts)
#
#             # this exception is usually NO_DATA_AVAILABLE_FOR_USER (happens when it is not initialized yet)
#             except self.cern.japc.core.ParameterException as xcp:
#
#                 # NO_DATA_AVAILABLE_FOR_USER
#                 self.modules_data[property] = [property, "No", str(xcp.getMessage()).split(":")[0], "-"]
#                 self.errors[property] = str(xcp)
#
#             # next iter
#             counter_property += 1
#
#             # emit the signal
#             self.processed.emit(self.modules_data, self.errors)
#
#             # sleep the thread a bit
#             QThread.msleep(100)
#
#         return

    #----------------------------------------------#

########################################################
########################################################

class GetWorkingDevicesThreadWorker(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(list, dict)

    #----------------------------------------------#

    # init function
    def __init__(self, device_list, acc_dev_list, japc, cern, old_working_devices, old_exception_dict):

        # inherit from QObject
        QObject.__init__(self)

        # declare attributes
        self.device_list = device_list
        self.acc_dev_list = acc_dev_list
        self.japc = japc
        self.cern = cern
        self.old_working_devices = old_working_devices
        self.old_exception_dict = old_exception_dict

        return

    #----------------------------------------------#

    # start function
    def start(self):

        # init the timer in terms of the RECHECK_DEVICES_PERIOD input variable (in seconds)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.getWorkingDevices)
        self._timer.start(RECHECK_DEVICES_PERIOD * 1000)

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # stop and emit the finish signal
        self._timer.stop()
        self.finished.emit()

        return

    #----------------------------------------------#

    # processing function
    def getWorkingDevices(self, verbose = False):

        # print thread address
        if verbose:
            print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))

        # declare the working devices list
        self.working_devices = []

        # save the exceptions in a dict
        self.exception_dict = {}

        # iterate over the devices
        for index_device, device in enumerate(self.device_list):

            # print the device for logging and debugging
            if verbose:
                print("{} - Checking the availability of {}".format(UI_FILENAME, device))

            # # use an empty selector for LHC devices
            # if self.acc_dev_list[index_device] == "LHC":
            #     selectorOverride = ""
            # # use SPS.USER.ALL for SPS devices
            # elif self.acc_dev_list[index_device] == "SPS":
            #     selectorOverride = "SPS.USER.SFTPRO1"
            # # use an empty selector for the others
            # else:
            #     selectorOverride = ""

            # use empty selector for GeneralInformation
            selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "GeneralInformation", "AutoGain"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

                # print the exception
                if verbose:
                    print("{} - Exception: cern.japc.core.ParameterException - {}".format(UI_FILENAME, xcp))
                    print("{} - Device {} is not working...".format(UI_FILENAME, device))

                # save the exception as xcp
                self.exception_dict[str(device)] = xcp

                # continue to the next device
                continue

            # append the device
            self.working_devices.append(device)

            # save the exception as empty
            self.exception_dict[str(device)] = ""

        # sleep the thread a bit
        QThread.sleep(5)

        # emit the signal that stores the working devices ONLY IF there were any changes
        if self.working_devices != self.old_working_devices:
            self.processed.emit(self.working_devices, self.exception_dict)

        return

    #----------------------------------------------#

########################################################
########################################################

class MyDisplay(CDisplay):

    #----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):

        return UI_FILENAME

    #----------------------------------------------#

    # event for closing the window in a right way
    def closeEventProgressDialog1ShowUp(self, evnt):

        # close event
        if self.progress_dialog_1_show_up_want_to_close:
            pass
        else:
            evnt.ignore()

        return

    # event for closing the window in a right way
    def closeEventProgressDialogAllCommands(self, evnt):

        # close event
        if self.progress_dialog_all_commands_want_to_close:
            pass
        else:
            evnt.ignore()

        return

    # event for closing the window in a right way
    def closeEventProgressDialogAfterRBAC(self, evnt):

        # close event
        if self.progress_dialog_after_rbac_want_to_close:
            pass
        else:
            evnt.ignore()

        return

    #----------------------------------------------#

    # closeEvent to ensure threads do finish correctly
    def closeEvent(self, event):

        # print
        print("{} - Closing the application...".format(UI_FILENAME))

        # do not do anything in case app was not yet initialized
        try:
            if self.aux_thread_for_preview_one_device:
                pass
            if self.acc_device_list_summary:
                pass
            if self.working_devices:
                pass
            if self.japc:
                pass
        except:
            return

        # stop old thread (preview_one_device)
        if type(self.aux_thread_for_preview_one_device) == QThread:
            if self.aux_thread_for_preview_one_device.isRunning():
                self.aux_worker_for_preview_one_device.stop()

        # stop old threads (summary)
        were_threads_running = False
        for device in self.acc_device_list_summary:
            if device in self.working_devices:
                if device in self.summary_thread_dict.keys():
                    if type(self.summary_thread_dict[device]) == QThread:
                        if self.summary_thread_dict[device].isRunning():
                            self.summary_worker_dict[device].stop()
                            were_threads_running = True

        # stop japc subs (summary)
        if were_threads_running:
            self.japc.stopSubscriptions()
            self.japc.clearSubscriptions()

        # finally clean up tmp data
        removeAppDir(TEMP_DIR_NAME)

        return

    #----------------------------------------------#


    # init function
    def __init__(self, *args, **kwargs):

        # use faulthandler to debug segmentation faults
        # faulthandler.enable()

        # init aux for qthread
        self.aux_thread_for_preview_one_device = 0
        self.summary_thread_dict = {}
        self.summary_worker_dict = {}
        self.acc_device_list_summary = []

        # create the temporary directory to store all the aux variables
        self.app_temp_dir = createCustomTempDir(TEMP_DIR_NAME)

        # init last index
        self.last_index_tree_view = 0

        # obtain all info about the devices via pyccda
        self.pyccda_dictionary = create_pyccda_json_file(query = QUERY, name_json_file = "pyccda_config.json", dir_json = self.app_temp_dir, verbose = False)

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # update closeEvent to ensure threads finish in the right way
        self.app.main_window.closeEvent = self.closeEvent

        # status bar message
        self.app.main_window.statusBar().showMessage("Loading main application window...", 0)
        self.app.main_window.statusBar().repaint()

        # this is not implemented yet in ComRAD
        # self.app._rbac._startup_login_policy = rbac.CRbaStartupLoginPolicy.LOGIN_EXPLICIT
        # self.app._rbac.startup_login()

        # aux variable for the after-fully-loaded-comrad operations
        self.is_comrad_fully_loaded = False

        # import cern package for handling exceptions
        self.cern = jp.JPackage("cern")

        # set current accelerator
        self.current_accelerator = "SPS"

        # get the device list and the accelerator-device relation list
        self.device_list = []
        self.acc_dev_list = []
        for acc_counter, acc_name in enumerate(self.pyccda_dictionary):
            if acc_counter == 0:
                self.device_list = list(self.pyccda_dictionary[acc_name].keys())
                self.acc_dev_list = [acc_name]*len(list(self.pyccda_dictionary[acc_name].keys()))
            else:
                self.device_list += list(self.pyccda_dictionary[acc_name].keys())
                self.acc_dev_list += [acc_name]*len(list(self.pyccda_dictionary[acc_name].keys()))

        # order the device list
        self.acc_dev_list = [x for _, x in sorted(zip(self.device_list, self.acc_dev_list))]
        self.device_list.sort()

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"

        # set the current window
        self.current_window = "premain"

        # create japc object
        self.japc = pyjapc.PyJapc()

        # get the devices that work
        self.getWorkingDevices(verbose = True)

        # init preloaded devices to show or not the progress dialog on preview_one_device.py
        self.preloaded_devices = set()

        # load the gui and set the title,
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("DIAMOND BLM EXPERT GUI")

        # init main window
        self.CEmbeddedDisplay.filename = ""

        # build the widgets and handle the signals
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # init the summary
        # self.selectAndClickTheRoot()

        # at this point comrad should be fully loaded
        self.is_comrad_fully_loaded = True

        # status bar message
        self.app.main_window.statusBar().clearMessage()
        self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # set icons
        self.toolButton_freeze.setIcon(QIcon("icons/freezing_1.png"))
        self.toolButton_main_settings.setIcon(QIcon("icons/settings.png"))
        self.toolButton_main_close.setIcon(QIcon("icons/close.png"))
        self.toolButton_main_back.setIcon(QIcon("icons/back.png"))

        # splitter to separate both panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.frame_device_selection)
        self.splitter.addWidget(self.frame_main_panel)
        self.splitter.setHandleWidth(0)
        self.splitter.setStretchFactor(0, 25)
        self.splitter.setStretchFactor(1, 75)
        self.horizontalLayout.addWidget(self.splitter)

        # build the device-list treeview
        self.model = QStandardItemModel()
        self.treeView.setModel(self.model)
        self.createTreeFromDeviceList()
        self.treeView.header().hide()
        self.treeView.setUniformRowHeights(True)
        self.treeView.expandAll()

        # set up the right-click menu handler
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openRightClickTreeMenu)

        return

    #----------------------------------------------#

    # this function sets up the menu that is opened when right-clicking the tree
    def openRightClickTreeMenu(self, position):

        # get the clicked element
        indexes = self.treeView.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            item = self.treeView.selectedIndexes()[0]
            selected_device = str(item.model().itemFromIndex(index).text())
            if selected_device != "SPS" and selected_device != "LHC" and selected_device != "NONE":
                selected_accelerator = str(item.model().itemFromIndex(index).parent().text())
            else:
                first_device = str(item.model().itemFromIndex(index).child(0,0).text())
                selected_accelerator = selected_device
                selected_device = ""
            while index.parent().isValid():
                index = index.parent()
                level += 1

        # create the menu
        menu = QMenu()

        # if the accelerator was selected get the commands of the first device
        if selected_device == "":
            command_list = list(self.pyccda_dictionary[selected_accelerator][first_device]["command"].keys())
        else:
            command_list = list(self.pyccda_dictionary[selected_accelerator][selected_device]["command"].keys())

        # init dict
        self.command_dict = {}

        # get start and stop commands
        start_commands = [i for i in command_list if i.find("Start") != -1]
        stop_commands = [i for i in command_list if i.find("Stop") != -1]

        # level 0 is either LHC or SPS (or NONE)
        if level == 0:
            self.command_dict["StartAll_{}".format(selected_device)] = menu.addAction(self.tr("Run StartAll ({}) on all {} devices".format(", ".join(start_commands), selected_accelerator)))
            self.command_dict["StartAll_{}".format(selected_device)].triggered.connect(lambda: self.commandActionAllStartAll(selected_accelerator))
            self.command_dict["StopAll_{}".format(selected_device)] = menu.addAction(self.tr("Run StopAll ({}) on all {} devices".format(", ".join(stop_commands), selected_accelerator)))
            self.command_dict["StopAll_{}".format(selected_device)].triggered.connect(lambda: self.commandActionAllStopAll(selected_accelerator))
            for command in command_list:
                self.command_dict[command] = menu.addAction(self.tr("Run {} on all {} devices".format(command, selected_accelerator)))
                self.command_dict[command].triggered.connect(lambda: self.commandActionAll(selected_accelerator))

        # level 1 are individual devices
        elif level == 1:
            self.command_dict["StartAll_{}".format(selected_device)] = menu.addAction(self.tr("Run StartAll ({}) on {}".format(", ".join(start_commands), selected_device)))
            self.command_dict["StartAll_{}".format(selected_device)].triggered.connect(lambda: self.commandActionStartAll(selected_device))
            self.command_dict["StopAll_{}".format(selected_device)] = menu.addAction(self.tr("Run StopAll ({}) on {}".format(", ".join(stop_commands), selected_device)))
            self.command_dict["StopAll_{}".format(selected_device)].triggered.connect(lambda: self.commandActionStopAll(selected_device))
            for command in command_list:
                self.command_dict[command] = menu.addAction(self.tr("Run {} on {}".format(command, selected_device)))
                self.command_dict[command].triggered.connect(lambda: self.commandAction(selected_device))

        # update view
        menu.exec_(self.treeView.viewport().mapToGlobal(position))

        return

    #----------------------------------------------#

    # function that runs the selected command on all the acc devices
    def commandActionAll(self, selected_accelerator):

        # get command name
        command = self.sender().text().split(" ")[1]

        # print
        print("{} - Running command {} on all {} devices...".format(UI_FILENAME, command, selected_accelerator))

        # get device list
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == selected_accelerator])

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # init progress bar
        counter_device = 0
        self.progress_dialog_all_commands = QProgressDialog("Running command {} on all {} devices...".format(command, selected_accelerator), None, 0, len(acc_device_list))
        # self.progress_dialog_all_commands.closeEvent = self.closeEventProgressDialogAllCommands
        self.progress_dialog_all_commands_want_to_close = False
        self.progress_dialog_all_commands.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog_all_commands.setAutoClose(False)
        self.progress_dialog_all_commands.setWindowTitle("Progress")
        self.progress_dialog_all_commands.setWindowIcon(QIcon("icons/diamond_2.png"))
        self.progress_dialog_all_commands.show()
        self.progress_dialog_all_commands.repaint()

        # iterate over devices
        for counter_device, selected_device in enumerate(acc_device_list):

            # update progress bar
            self.progress_dialog_all_commands.setValue(counter_device)
            self.progress_dialog_all_commands.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # status bar message
            self.app.main_window.statusBar().showMessage("Running command {} on all {} devices ({}/{})...".format(command, selected_accelerator, counter_device+1, len(acc_device_list)), 0)
            self.app.main_window.statusBar().repaint()

            # send an empty dict to perform a COMMAND operation via pyjapc
            try:
                self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
            except Exception as xcp:
                exception = xcp
                print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                exception_dev_list.append(selected_device)

        # close progress bar
        self.progress_dialog_all_commands_want_to_close = True
        self.progress_dialog_all_commands.close()

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running command {} on all {} devices!".format(command, selected_accelerator), 10*1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command {}".format(command)
            message_text = "Command {} ran successfully on all {} devices.".format(command, selected_accelerator)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            if len(exception_dev_list) == len(acc_device_list):
                message_title = "Command {}".format(command)
                message_text = "Unable to run command {} on any of the {} devices.".format(command, selected_accelerator)
                self.message_box = QMessageBox.critical(self, message_title, message_text)
            else:
                message_title = "Command {}".format(command)
                message_text = "Unable to run command {} on the following devices: {}. Command ran successfully in the others though.".format(command, ', '.join(exception_dev_list))
                self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that runs start commands on all the acc devices
    def commandActionAllStartAll(self, selected_accelerator):

        # get command name
        full_string = self.sender().text()
        commands = full_string[full_string.find("(") + 1:full_string.find(")")]
        commands = commands.split(", ")

        # print
        print("{} - Running StartAll command on all {} devices...".format(UI_FILENAME, selected_accelerator))

        # get device list
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == selected_accelerator])

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # init progress bar
        counter_device = 0
        self.progress_dialog_all_commands = QProgressDialog("Running StartAll command on all {} devices...".format(selected_accelerator), None, 0, len(acc_device_list))
        # self.progress_dialog_all_commands.closeEvent = self.closeEventProgressDialogAllCommands
        self.progress_dialog_all_commands_want_to_close = False
        self.progress_dialog_all_commands.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog_all_commands.setAutoClose(False)
        self.progress_dialog_all_commands.setWindowTitle("Progress")
        self.progress_dialog_all_commands.setWindowIcon(QIcon("icons/diamond_2.png"))
        self.progress_dialog_all_commands.show()
        self.progress_dialog_all_commands.repaint()

        # iterate over devices
        for counter_device, selected_device in enumerate(acc_device_list):

            # update progress bar
            self.progress_dialog_all_commands.setValue(counter_device)
            self.progress_dialog_all_commands.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # status bar message
            self.app.main_window.statusBar().showMessage("Running StartAll command on all {} devices ({}/{})...".format(selected_accelerator, counter_device + 1, len(acc_device_list)), 0)
            self.app.main_window.statusBar().repaint()

            # iterate over commands
            for command in commands:

                # send an empty dict to perform a COMMAND operation via pyjapc
                try:
                    self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
                except Exception as xcp:
                    exception = xcp
                    print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                    exception_dev_list.append(selected_device)
                    break

        # close progress bar
        self.progress_dialog_all_commands_want_to_close = True
        self.progress_dialog_all_commands.close()

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running StartAll command on all {} devices!".format(selected_accelerator), 10 * 1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command StartAll"
            message_text = "Command StartAll ran successfully on all {} devices.".format(selected_accelerator)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            if len(exception_dev_list) == len(acc_device_list):
                message_title = "Command StartAll".format(command)
                message_text = "Unable to run StartAll command on any of the {} devices.".format(selected_accelerator)
                self.message_box = QMessageBox.critical(self, message_title, message_text)
            else:
                message_title = "Command StartAll"
                message_text = "Unable to run StartAll command on the following devices: {}. Command ran successfully in the others though.".format(', '.join(exception_dev_list))
                self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#


    # function that runs stop commands on all the acc devices
    def commandActionAllStopAll(self, selected_accelerator):

        # get command name
        full_string = self.sender().text()
        commands = full_string[full_string.find("(") + 1:full_string.find(")")]
        commands = commands.split(", ")

        # print
        print("{} - Running StopAll command on all {} devices...".format(UI_FILENAME, selected_accelerator))

        # get device list
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == selected_accelerator])

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # init progress bar
        counter_device = 0
        self.progress_dialog_all_commands = QProgressDialog("Running StopAll command on all {} devices...".format(selected_accelerator), None, 0, len(acc_device_list))
        # self.progress_dialog_all_commands.closeEvent = self.closeEventProgressDialogAllCommands
        self.progress_dialog_all_commands_want_to_close = False
        self.progress_dialog_all_commands.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog_all_commands.setAutoClose(False)
        self.progress_dialog_all_commands.setWindowTitle("Progress")
        self.progress_dialog_all_commands.setWindowIcon(QIcon("icons/diamond_2.png"))
        self.progress_dialog_all_commands.show()
        self.progress_dialog_all_commands.repaint()

        # iterate over devices
        for counter_device, selected_device in enumerate(acc_device_list):

            # update progress bar
            self.progress_dialog_all_commands.setValue(counter_device)
            self.progress_dialog_all_commands.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # status bar message
            self.app.main_window.statusBar().showMessage("Running StopAll command on all {} devices ({}/{})...".format(selected_accelerator, counter_device + 1, len(acc_device_list)), 0)
            self.app.main_window.statusBar().repaint()

            # iterate over commands
            for command in commands:

                # send an empty dict to perform a COMMAND operation via pyjapc
                try:
                    self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
                except Exception as xcp:
                    exception = xcp
                    print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                    exception_dev_list.append(selected_device)
                    break

        # close progress bar
        self.progress_dialog_all_commands_want_to_close = True
        self.progress_dialog_all_commands.close()

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running StopAll command on all {} devices!".format(selected_accelerator), 10 * 1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command StopAll"
            message_text = "Command StopAll ran successfully on all {} devices.".format(selected_accelerator)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            if len(exception_dev_list) == len(acc_device_list):
                message_title = "Command StopAll".format(command)
                message_text = "Unable to run StopAll command on any of the {} devices.".format(selected_accelerator)
                self.message_box = QMessageBox.critical(self, message_title, message_text)
            else:
                message_title = "Command StopAll"
                message_text = "Unable to run StopAll command on the following devices: {}. Command ran successfully in the others though.".format(', '.join(exception_dev_list))
                self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that runs the selected command on the selected device
    def commandAction(self, selected_device):

        # get command name
        command = self.sender().text().split(" ")[1]

        # status bar message
        self.app.main_window.statusBar().showMessage("Running command {} on {}...".format(command, selected_device), 0)
        self.app.main_window.statusBar().repaint()

        # print
        print("{} - Running command {} on {}...".format(UI_FILENAME, command, selected_device))

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # send an empty dict to perform a COMMAND operation via pyjapc
        try:
            self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
        except Exception as xcp:
            exception = xcp
            print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
            exception_dev_list.append(selected_device)

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running command {} on {}!".format(command, selected_device), 10*1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command {}".format(command)
            message_text = "Command {} ran successfully on {}.".format(command, selected_device)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            message_title = "Command {}".format(command)
            message_text = "Unable to run command {} on {} due to the following exception: {}".format(command, selected_device, exception)
            self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that runs all start commands
    def commandActionStartAll(self, selected_device):

        # get command name
        full_string = self.sender().text()
        commands = full_string[full_string.find("(") + 1:full_string.find(")")]
        commands = commands.split(", ")

        # status bar message
        self.app.main_window.statusBar().showMessage("Running StartAll command on {}...".format(selected_device), 0)
        self.app.main_window.statusBar().repaint()

        # print
        print("{} - Running StartAll command on {}...".format(UI_FILENAME, selected_device))

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # iterate over commands
        for command in commands:

            # send an empty dict to perform a COMMAND operation via pyjapc
            try:
                self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
            except Exception as xcp:
                exception = xcp
                print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                exception_dev_list.append(selected_device)
                break

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running StartAll command on {}!".format(selected_device), 10 * 1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command StartAll"
            message_text = "Command StartAll ran successfully on {}.".format(selected_device)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            message_title = "Command StartAll"
            message_text = "Unable to run StartAll command on {} due to the following exception: {}".format(selected_device, exception)
            self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that runs all stop commands
    def commandActionStopAll(self, selected_device):

        # get command name
        full_string = self.sender().text()
        commands = full_string[full_string.find("(") + 1:full_string.find(")")]
        commands = commands.split(", ")

        # status bar message
        self.app.main_window.statusBar().showMessage("Running StopAll command on {}...".format(selected_device), 0)
        self.app.main_window.statusBar().repaint()

        # print
        print("{} - Running StopAll command on {}...".format(UI_FILENAME, selected_device))

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # iterate over commands
        for command in commands:

            # send an empty dict to perform a COMMAND operation via pyjapc
            try:
                self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
            except Exception as xcp:
                exception = xcp
                print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                exception_dev_list.append(selected_device)
                break

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running StopAll command on {}!".format(selected_device), 10 * 1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command StopAll"
            message_text = "Command StopAll ran successfully on {}.".format(selected_device)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            message_title = "Command StopAll"
            message_text = "Unable to run StopAll command on {} due to the following exception: {}".format(selected_device, exception)
            self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # either shows the preview or the summary whenever an item from the treeview is clicked
        self.treeView.clicked.connect(self.itemFromTreeviewClicked)

        # close main device window when pressing the close toolbutton
        self.toolButton_main_close.clicked.connect(self.closeMain)

        # open settings window (mainly for the getters and setters)
        self.toolButton_main_settings.clicked.connect(self.goToSettingsWindow)

        # back to the last window (which can be preview or main)
        self.toolButton_main_back.clicked.connect(self.backToLastWindow)

        # send freeze information when pressing the freeze toolbutton
        self.toolButton_freeze.toggled.connect(self.sendFreezeText)

        # set up a timer to open the devices when the OPEN DEVICE button is pressed
        self.timer_open_device = QTimer(self)
        self.timer_open_device.setInterval(1000)
        self.timer_open_device.timeout.connect(self.isOpenDevicePushButtonPressed)
        self.timer_open_device.start()

        # set up a timer to HACK comrad after it is fully loaded
        self.timer_hack_operations_after_comrad_is_fully_loaded = QTimer(self)
        self.timer_hack_operations_after_comrad_is_fully_loaded.setInterval(100)
        self.timer_hack_operations_after_comrad_is_fully_loaded.timeout.connect(self.doOperationsAfterComradIsFullyLoaded)
        self.timer_hack_operations_after_comrad_is_fully_loaded.start()

        # selector signal
        self.app.main_window.window_context.selectorChanged.connect(self.selectorWasChanged)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        # recheck if the devices keep working in another thread
        self.aux_thread = QThread(parent=self)
        self.aux_worker = GetWorkingDevicesThreadWorker(self.device_list, self.acc_dev_list, self.japc, self.cern, self.working_devices, self.exception_dict)
        self.aux_worker.moveToThread(self.aux_thread)
        self.aux_worker.finished.connect(self.finishThread)
        self.aux_thread.started.connect(self.aux_worker.start)
        self.aux_thread.start()

        # update the devices once the thread outputs the results
        self.aux_worker.processed.connect(self.updateWorkingDevices)

        return

    #----------------------------------------------#

    # function to handle thread stops
    def finishThread(self):

        # quit the thread
        self.aux_thread.quit()
        self.aux_thread.wait()

        return

    # function to handle thread stops
    def finishThreadPreviewOneDevice(self):

        # quit the thread
        self.aux_thread_for_preview_one_device.quit()
        self.aux_thread_for_preview_one_device.wait()

        return

    # function to handle thread stops
    def finishThreadSummary(self):

        # quit the threads
        for device in self.acc_device_list_summary:
            if device in self.summary_thread_dict.keys():
                self.summary_thread_dict[device].quit()
                self.summary_thread_dict[device].wait()

        return

    # function to handle thread stops
    def finishThread1ShowUp(self):

        # quit the threads
        for r in range(0, self.len_iters_1_show_up):
            if r in self.aux_thread_dict.keys():
                self.aux_thread_dict[r].quit()
                self.aux_thread_dict[r].wait()

        return

    #----------------------------------------------#

    # function that handles japc and UI stuff when rbac is disconnected
    def rbacLogoutSucceeded(self):

        # print message
        print("{} - RBAC logout succeeded...".format(UI_FILENAME))

        # end pyjapc rbac connection
        self.japc.rbacLogout()

        # get working devices again
        self.getWorkingDevices(verbose = False)

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon("icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("icons/red_cross.png"))

        # update UI
        if self.current_window == "preview" or self.current_window == "summary" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

        return

    #----------------------------------------------#

    # this function gets activated whenever RBAC logins successfully
    def rbacLoginSucceeded(self):

        # progress bar init
        counter_device = 0
        self.progress_dialog_after_rbac = QProgressDialog("Updating devices after a successful RBAC login...", None, 0, len(self.device_list))
        # self.progress_dialog_after_rbac.closeEvent = self.closeEventProgressDialogAfterRBAC
        self.progress_dialog_after_rbac_want_to_close = False
        self.progress_dialog_after_rbac.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog_after_rbac.setAutoClose(False)
        self.progress_dialog_after_rbac.setWindowTitle("Progress")
        self.progress_dialog_after_rbac.setWindowIcon(QIcon("icons/diamond_2.png"))
        self.progress_dialog_after_rbac.show()
        self.progress_dialog_after_rbac.repaint()

        # print message
        print("{} - RBAC login succeeded...".format(UI_FILENAME))

        # save the token into the environmental variable so that we can read it with pyjapc
        os.environ["RBAC_TOKEN_SERIALIZED"] = self.app._rbac.serialized_token

        # now that we have a token try to login with japc too
        self.japc.rbacLogin(readEnv=True)

        # get working devices again
        self.getWorkingDevices(verbose = False, from_rbac = True)

        # HACK TO SPEED UP OPENING SUMMARY LATER ON

        # get first working device of LHC
        first_working_device = None
        if "LHC" in self.acc_dev_list:
            acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == "LHC"])
            for dev in acc_device_list:
                if dev in self.working_devices:
                    first_working_device = dev
                    break

        # first subs
        if first_working_device:
            self.japc.subscribeParam("{}/{}".format(first_working_device, "AcquisitionHistogram"), onValueReceived=self.subsCallbackEmpty, onException=self.onExceptionEmpty, timingSelectorOverride="", getHeader=True)
            self.japc.startSubscriptions()
            self.japc.stopSubscriptions()
            self.japc.clearSubscriptions()

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon("icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("icons/red_cross.png"))

        # close progress bar
        self.progress_dialog_after_rbac_want_to_close = True
        self.progress_dialog_after_rbac.close()

        # update UI (the preview panels)
        if self.current_window == "preview" or self.current_window == "summary" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

        return

    #----------------------------------------------#

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        self.current_selector = self.app.main_window.window_context.selector
        print("{} - New selector is: {}".format(UI_FILENAME, self.current_selector))

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that checks which devices are properly working and which are not
    def getWorkingDevices(self, verbose = True, from_rbac = False):

        # declare the working devices list
        self.working_devices = []

        # save the exceptions in a dict
        self.exception_dict = {}

        # iterate over the devices
        for index_device, device in enumerate(self.device_list):

            # status bar message
            if from_rbac:
                self.app.main_window.statusBar().showMessage("Successful RBAC login! Checking availability of new devices ({}/{})...".format(index_device+1, len(self.device_list)), 0)
                self.app.main_window.statusBar().repaint()
                self.progress_dialog_after_rbac.setValue(index_device)
                self.progress_dialog_after_rbac.repaint()
                self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # print the device for logging and debugging
            if verbose:
                print("{} - Checking the availability of {}".format(UI_FILENAME, device))

            # # use an empty selector for LHC devices
            # if self.acc_dev_list[index_device] == "LHC":
            #     selectorOverride = ""
            # # use SPS.USER.ALL for SPS devices
            # elif self.acc_dev_list[index_device] == "SPS":
            #     selectorOverride = "SPS.USER.SFTPRO1"
            # # use an empty selector for the others
            # else:
            #     selectorOverride = ""

            # use empty selector for GeneralInformation
            selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "GeneralInformation", "AutoGain"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

                # print the exception
                if verbose:
                    print("{} - Exception: cern.japc.core.ParameterException - {}".format(UI_FILENAME, xcp))
                    print("{} - Device {} is not working...".format(UI_FILENAME, device))

                # save the exception as xcp
                self.exception_dict[str(device)] = xcp

                # continue to the next device
                continue

            # append the device
            self.working_devices.append(device)

            # save the exception as empty
            self.exception_dict[str(device)] = ""

        # status bar message
        if from_rbac:
            self.app.main_window.statusBar().showMessage("Device availability check finished! {}/{} devices working right now!".format(len(self.working_devices), len(self.device_list)), 10*1000)
            self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that updates the working devices (remember signal is only emitted when there are changes in the list)
    def updateWorkingDevices(self, working_devices, exception_dict, verbose = False):

        # print message
        if verbose:
            print("{} - Updating working devices!".format(UI_FILENAME))

        # update variables
        self.working_devices = working_devices
        self.exception_dict = exception_dict

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon("icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("icons/red_cross.png"))

        # update UI (the preview panels)
        # if self.current_window == "preview" or self.current_window == "premain":
        #     if self.last_index_tree_view != 0:
        #         self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

        return

    #----------------------------------------------#

    # function that adds the items to the tree view
    def createTreeFromDeviceList(self):

        # init row and column counts
        self.model.setRowCount(0)
        self.model.setColumnCount(0)

        # create a root for every accelerator (LHC and SPS)
        for acc_counter, acc_name in enumerate(self.pyccda_dictionary):

            # set up the root
            root = QStandardItem(acc_name)

            # get accelerator specific devices
            acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == acc_name])

            # append items to the root
            for device in acc_device_list:

                # define the item to append
                itemToAppend = QStandardItem("{}".format(device))

                # determine the icon (working or not)
                if device in self.working_devices:
                    itemToAppend.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                    itemToAppend.setIcon(QIcon("icons/green_tick.png"))
                else:
                    itemToAppend.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                    itemToAppend.setIcon(QIcon("icons/red_cross.png"))

                # append it to the tree
                root.appendRow(itemToAppend)

            # append the root to the model
            self.model.appendRow(root)

            # get the index of the root (THIS HAS TO BE THE LAST LINE OF CODE AFTER THE TREE IS CREATED SO THAT THE INDEX ACTUALLY POINTS TO THE RIGHT ELEMENT OF THE TREE)
            if acc_counter == 0:
                self.index_of_the_root = root.index()

        return

    #----------------------------------------------#

    # function that selects and clicks the root (e.g. SPS) to init tshe summary
    def selectAndClickTheRoot(self):

        # initialize the summary by selecting and clicking the root
        self.treeView.selectionModel().select(self.index_of_the_root, QItemSelectionModel.Select)
        self.itemFromTreeviewClicked(self.index_of_the_root, ignore_checking = True)

        return

    #----------------------------------------------#

    # function that shows the device preview when a device is clicked
    def itemFromTreeviewClicked(self, index, ignore_checking = False):

        # if the user clicked the same just skip
        if not ignore_checking:
            if index == self.last_index_tree_view:
                return

        # store last index
        self.last_index_tree_view = index

        # read the name of the device
        item = self.treeView.selectedIndexes()[0]
        selected_text = str(item.model().itemFromIndex(index).text())
        print("{} - Clicked from treeView: {}".format(UI_FILENAME, selected_text))

        # if the item IS NOT the root, then show the preview
        if selected_text != "SPS" and selected_text != "LHC" and selected_text != "NONE":

            # get the parent (cycle) text (e.g. LHC or SPS)
            parent_text = str(item.model().itemFromIndex(index).parent().text())

            # update selector
            if parent_text == "SPS":
                self.app.main_window.window_context.selector = 'SPS.USER.ALL'
            elif parent_text == "LHC":
                self.app.main_window.window_context.selector = ''
            elif parent_text == "NONE":
                self.app.main_window.window_context.selector = ''

            # update the current device
            self.current_device = selected_text
            self.current_accelerator = parent_text
            self.preloaded_devices.add(self.current_device)
            self.writeDeviceIntoTxtForSubWindows(self.current_accelerator)

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading device preview...", 0)
            self.app.main_window.statusBar().repaint()

            # stop old thread (preview_one_device)
            if type(self.aux_thread_for_preview_one_device) == QThread:
                if self.aux_thread_for_preview_one_device.isRunning():
                    self.aux_worker_for_preview_one_device.stop()

            # stop old threads (summary)
            were_threads_running = False
            for device in self.acc_device_list_summary:
                if device in self.working_devices:
                    if device in self.summary_thread_dict.keys():
                        if type(self.summary_thread_dict[device]) == QThread:
                            if self.summary_thread_dict[device].isRunning():
                                self.summary_worker_dict[device].stop()
                                were_threads_running = True

            # stop japc subs (summary)
            if were_threads_running:
                self.japc.stopSubscriptions()
                self.japc.clearSubscriptions()

            # clear for new device
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates")):
                shutil.rmtree(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates"))

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_one_device.py"
            self.CEmbeddedDisplay.open_file()

            # thread for preview only if device is working
            if self.current_device in self.working_devices:

                # get the property list
                self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())

                # order the property list
                self.property_list.sort()

                # recheck if the modes are working each x seconds
                self.aux_thread_for_preview_one_device = QThread(parent=self)
                self.aux_worker_for_preview_one_device = workingModesThreadWorkerPreview(self.current_device, self.current_accelerator, self.japc, self.property_list, self.cern, self.pyccda_dictionary)
                self.aux_worker_for_preview_one_device.moveToThread(self.aux_thread_for_preview_one_device)
                self.aux_worker_for_preview_one_device.finished.connect(self.finishThreadPreviewOneDevice)
                self.aux_thread_for_preview_one_device.started.connect(self.aux_worker_for_preview_one_device.start)
                self.aux_thread_for_preview_one_device.start()

                # update once the thread outputs the results
                self.aux_worker_for_preview_one_device.processed.connect(self.sendUpdatesWorkingModesPreview)

            # update text label
            if self.current_device in self.working_devices:
                self.label_device_panel.setText("DEVICE PANEL <font color=green>{}</font> : <font color=green>{}</font>".format(parent_text, self.current_device))
            else:
                self.label_device_panel.setText( "DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format(parent_text, self.current_device))

            # enable tool buttons
            if self.current_device in self.working_devices:
                self.toolButton_main_settings.setEnabled(True)
            else:
                self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
            self.toolButton_main_close.setEnabled(True)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "preview"

        # if the item IS the root, then show the summary
        else:

            # update selector
            if selected_text == "SPS":
                self.app.main_window.window_context.selector = 'SPS.USER.ALL'
            elif selected_text == "LHC":
                self.app.main_window.window_context.selector = ''
            elif selected_text == "NONE":
                self.app.main_window.window_context.selector = ''

            # send and write the device list
            self.current_accelerator = selected_text
            for pre_dev in list(np.array(self.device_list)[np.array(self.acc_dev_list) == self.current_accelerator]):
                self.preloaded_devices.add(pre_dev)
            self.writeDeviceIntoTxtForSubWindows(self.current_accelerator)

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading {} summary preview...".format(self.current_accelerator), 0)
            self.app.main_window.statusBar().repaint()

            # get accelerator specific devices
            acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == self.current_accelerator])
            self.acc_device_list_summary = acc_device_list

            # stop old thread (preview_one_device)
            if type(self.aux_thread_for_preview_one_device) == QThread:
                if self.aux_thread_for_preview_one_device.isRunning():
                    self.aux_worker_for_preview_one_device.stop()

            # stop old threads (summary)
            were_threads_running = False
            for device in self.acc_device_list_summary:
                if device in self.working_devices:
                    if device in self.summary_thread_dict.keys():
                        if type(self.summary_thread_dict[device]) == QThread:
                            if self.summary_thread_dict[device].isRunning():
                                self.summary_worker_dict[device].stop()
                                were_threads_running = True

            # stop japc subs (summary)
            if were_threads_running:
                self.japc.stopSubscriptions()
                self.japc.clearSubscriptions()

            # clear for new device
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates")):
                shutil.rmtree(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates"))

            # START the processing of the FIRST SHOW UP of the summary (e.g. progress bar)

            # clear previous summary data
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up")):
                shutil.rmtree(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up"))

            # init thread dicts
            self.aux_thread_dict = {}
            self.aux_worker_dict = {}

            # init model data list of lists
            self.summary_data_1_show_up = []
            self.error_dict_1_show_up = {}
            self.not_sort_summary_data_1_show_up = {}
            self.received_rs = []

            # variables needed for the first show up
            field_list_1_show_up = ["BeamMomentum", "BstShift", "BunchSample", "FpgaCompilation", "FpgaFirmware", "FpgaStatus", "TurnBc", "TurnDropped", "TurnSample"]
            property_list_1_show_up = list(self.pyccda_dictionary[self.current_accelerator][acc_device_list[0]]["acquisition"].keys())
            property_list_1_show_up.sort()
            self.len_iters_1_show_up = len(field_list_1_show_up) + len(property_list_1_show_up)
            self.summary_header_labels_horizontal_1_show_up = ["Field / Mode"] + acc_device_list

            # number of iterations of working devices
            len_working_devices = 0
            for device in self.acc_device_list_summary:
                if device in self.working_devices:
                    property_list = list(self.pyccda_dictionary[self.current_accelerator][device]["acquisition"].keys())
                    for property in property_list:
                        if property != "GeneralInformation":
                            len_working_devices += 1

            # init progress bar
            self.progress_maximum_iters = (self.len_iters_1_show_up - 1) * len(acc_device_list) + len_working_devices + 5
            self.progress_dialog_1_show_up = QProgressDialog("Opening summary view for {} devices...".format(self.current_accelerator), None, 0, self.progress_maximum_iters)
            self.progress_dialog_1_show_up.closeEvent = self.closeEventProgressDialog1ShowUp
            self.progress_dialog_1_show_up_want_to_close = False
            self.progress_dialog_1_show_up.setWindowModality(Qt.ApplicationModal)
            self.progress_dialog_1_show_up.setAutoClose(False)
            self.progress_dialog_1_show_up.setWindowTitle("Progress")
            self.progress_dialog_1_show_up.setWindowIcon(QIcon("icons/diamond_2.png"))
            self.progress_dialog_1_show_up.setValue(0)
            self.progress_dialog_1_show_up.show()
            self.progress_dialog_1_show_up.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)
            self.dialog_counter = 0

            # iterate over fields and properties
            for r in range(0, self.len_iters_1_show_up):

                # create thread
                self.aux_thread_dict[r] = QThread(parent=self)
                self.aux_worker_dict[r] = GetFieldInfoThreadWorker1ShowUp(r, acc_device_list, property_list_1_show_up, field_list_1_show_up, self.working_devices, self.current_accelerator, self.pyccda_dictionary, self.japc, self.cern)
                self.aux_worker_dict[r].moveToThread(self.aux_thread_dict[r])
                self.aux_worker_dict[r].finished.connect(self.finishThread1ShowUp)
                self.aux_thread_dict[r].started.connect(self.aux_worker_dict[r].start)
                self.aux_thread_dict[r].start()

                # bind thread
                self.aux_worker_dict[r].processed.connect(self.updateModelDicts1ShowUp)
                self.aux_worker_dict[r].iterated.connect(self.updateDialogCounter1ShowUp)

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_summary.py"
            self.CEmbeddedDisplay.open_file()

            # update dialog counter
            self.dialog_counter += 5

            # update progress bar
            self.progress_dialog_1_show_up.setValue(self.dialog_counter)
            self.progress_dialog_1_show_up.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # START the processing of the SECOND SHOW UP of the summary (e.g. QThreads for updating the table each 1 second)

            # init summary thread and worker dict
            self.summary_thread_dict = {}
            self.summary_worker_dict = {}

            # init subs aux variables
            DATA_SUBS_SUMMARY = {}
            LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY = {}

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

            # threads for summary view
            for device in self.acc_device_list_summary:

                # check device works
                if device in self.working_devices:

                    # get the property list
                    property_list = list(self.pyccda_dictionary[self.current_accelerator][device]["acquisition"].keys())

                    # order the property list
                    property_list.sort()

                    # create subs
                    for property in property_list:

                        # ignore general info
                        if property != "GeneralInformation":

                            # start subs
                            self.japc.subscribeParam("{}/{}".format(device, property), onValueReceived=self.subsCallbackSummary, onException=self.onExceptionSummary, timingSelectorOverride=selectorOverride, getHeader=True)
                            self.japc.startSubscriptions()

                            # update dialog counter
                            self.dialog_counter += 1

                            # update progress bar
                            self.progress_dialog_1_show_up.setValue(self.dialog_counter)
                            self.progress_dialog_1_show_up.repaint()
                            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

                            # close progress bar
                            if self.dialog_counter == self.progress_maximum_iters:
                                self.progress_dialog_1_show_up_want_to_close = True
                                self.progress_dialog_1_show_up.close()

                    # recheck if the modes are working each x seconds
                    self.summary_thread_dict[device] = QThread(parent=self)
                    self.summary_worker_dict[device] = workingModesThreadWorkerSummary(device, self.acc_device_list_summary, self.current_accelerator, self.japc, property_list, self.cern, self.pyccda_dictionary)
                    self.summary_worker_dict[device].moveToThread(self.summary_thread_dict[device])
                    self.summary_worker_dict[device].finished.connect(self.finishThreadSummary)
                    self.summary_thread_dict[device].started.connect(self.summary_worker_dict[device].start)
                    self.summary_thread_dict[device].start()

                    # update once the thread outputs the results
                    self.summary_worker_dict[device].processed.connect(self.sendUpdatesWorkingModesSummary)

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=black>{}</font> : <font color=black>{}</font>".format(selected_text, "SUMMARY"))

            # enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
            self.toolButton_main_close.setEnabled(True)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "summary"
            
    #----------------------------------------------#

    # function that updates the dialog counter of the progress bar
    def updateDialogCounter1ShowUp(self):

        # update dialog counter
        self.dialog_counter += 1

        # update progress bar
        self.progress_dialog_1_show_up.setValue(self.dialog_counter)
        self.progress_dialog_1_show_up.repaint()
        self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

        # close progress bar
        if self.dialog_counter == self.progress_maximum_iters:
            self.progress_dialog_1_show_up_want_to_close = True
            self.progress_dialog_1_show_up.close()

        return

    #----------------------------------------------#

    # function that receives data from the threads and updates GUI on preview_summary.py
    def updateModelDicts1ShowUp(self, r, row_list, row_error_dict, is_general_information):

        # append r
        self.received_rs.append(r)

        # skip general information
        if not is_general_information:

            # insert data and error
            self.not_sort_summary_data_1_show_up[r] = row_list
            self.error_dict_1_show_up[r] = row_error_dict

        # update the table when the last row is received
        if len(self.received_rs) == self.len_iters_1_show_up:

            # sort summary data
            sort_dict = collections.OrderedDict(sorted(self.not_sort_summary_data_1_show_up.items()))
            self.summary_data_1_show_up = [sort_dict[key] for key in sort_dict]

            # stop all threads
            for r in range(0, self.len_iters_1_show_up):
                if r in self.aux_thread_dict.keys():
                    if type(self.aux_thread_dict[r]) == QThread:
                        if self.aux_thread_dict[r].isRunning():
                            self.aux_worker_dict[r].stop()

            # write all data to a json that preview_summary can read
            if not os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up")):
                os.mkdir(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up"))
            with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_data.json"), "w") as fp:
                json.dump(self.summary_data_1_show_up, fp, sort_keys=True, indent=4)
            with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "error_dict.json"), "w") as fp:
                json.dump(self.error_dict_1_show_up, fp, sort_keys=True, indent=4)
            with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_1_show_up", "summary_header_labels_horizontal.json"), "w") as fp:
                json.dump(self.summary_header_labels_horizontal_1_show_up, fp, sort_keys=True, indent=4)

        return

    #----------------------------------------------#

    # empty handlers
    def onExceptionEmpty(self):
        return
    def subsCallbackEmpty(self):
        return

    #----------------------------------------------#

    # function that handles pyjapc exceptions
    def onExceptionSummary(self, parameterName, description, exception, verbose = False):

        # print
        if verbose:
            print("{} - Exception: {}".format(UI_FILENAME, exception))

        # nothing
        pass

        return

    #----------------------------------------------#

    # function to receive pyjapc subs data
    def subsCallbackSummary(self, parameterName, dictValues, headerInfo, verbose = False):

        # get device name
        dev_name = parameterName.split("/")[0]

        # get property name
        prop_name = parameterName.split("/")[1]

        # ignore GeneralInformation
        if prop_name == "GeneralInformation":
            return

        # init keys
        if not dev_name in DATA_SUBS_SUMMARY.keys():
            DATA_SUBS_SUMMARY[dev_name] = {}
        if not dev_name in LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY.keys():
            LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[dev_name] = {}

        # store the data
        DATA_SUBS_SUMMARY[dev_name][prop_name] = dictValues

        # store last timestamp of the callback
        LAST_TIMESTAMP_SUB_CALLBACK_SUMMARY[dev_name][prop_name] = headerInfo["acqStamp"]

        # print
        if verbose:
            print("{} - Received {} values for {}...".format(UI_FILENAME, prop_name, dev_name))

        return

    #----------------------------------------------#

    # function that closes the main device window
    def closeMain(self):

        # print the action
        print("{} - Button CLOSE pressed".format(UI_FILENAME))

        # close main container
        if self.CEmbeddedDisplay.filename != "":

            # status bar message
            self.app.main_window.statusBar().showMessage("Main window closed!", 5*1000)
            self.app.main_window.statusBar().repaint()

            # stop old thread (preview_one_device)
            if type(self.aux_thread_for_preview_one_device) == QThread:
                if self.aux_thread_for_preview_one_device.isRunning():
                    self.aux_worker_for_preview_one_device.stop()

            # stop old threads (summary)
            were_threads_running = False
            for device in self.acc_device_list_summary:
                if device in self.working_devices:
                    if device in self.summary_thread_dict.keys():
                        if type(self.summary_thread_dict[device]) == QThread:
                            if self.summary_thread_dict[device].isRunning():
                                self.summary_worker_dict[device].stop()
                                were_threads_running = True

            # stop japc subs (summary)
            if were_threads_running:
                self.japc.stopSubscriptions()
                self.japc.clearSubscriptions()

            # update main panel
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format("NO CYCLE SELECTED", "NO DEVICE SELECTED"))

            # disable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
            self.toolButton_main_close.setEnabled(False)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "premain"

            # reset last index
            self.last_index_tree_view = 0

        return

    #----------------------------------------------#

    # function that opens the settings window that shows the different configurable parameters of the device
    def goToSettingsWindow(self):

        # print the action
        print("{} - Button SETTINGS pressed".format(UI_FILENAME))

        # write the selector
        self.writeSelectorIntoTxt()

        # open settings window
        if self.CEmbeddedDisplay.filename != "":

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading settings...", 0)
            self.app.main_window.statusBar().repaint()

            # update main panel
            # self.CEmbeddedDisplay.filename = ""
            # self.CEmbeddedDisplay.hide()
            # self.CEmbeddedDisplay.show()
            # self.CEmbeddedDisplay.filename = "settings_dialog_auto.py"
            # self.CEmbeddedDisplay.open_file()

            # open the dialog
            self.settings_dialog_auto = SettingsDialogAuto(parent=self)
            self.settings_dialog_auto.setModal(False)
            self.settings_dialog_auto.show()
            self.settings_dialog_auto.nturns_changed.connect(self.notifyNturnChanged)

            # disable and enable tool buttons
            # self.toolButton_main_settings.setEnabled(False)
            # self.toolButton_freeze.setEnabled(False)
            # self.toolButton_main_close.setEnabled(True)
            # self.toolButton_main_back.setEnabled(True)

            # update the current window
            # self.current_window = "settings"

    #----------------------------------------------#

    # function that notifies preview workers if nturn changed in the settings menu after a set call
    def notifyNturnChanged(self):

        # print
        print("{} - The parameter nturn changed!".format(UI_FILENAME))

        # stop old thread and restart (preview_one_device)
        if type(self.aux_thread_for_preview_one_device) == QThread:
            if self.aux_thread_for_preview_one_device.isRunning():
                self.aux_worker_for_preview_one_device.stop()
                sleep(0.1)
                self.aux_thread_for_preview_one_device = QThread(parent=self)
                self.aux_worker_for_preview_one_device = workingModesThreadWorkerPreview(self.current_device, self.current_accelerator, self.japc, self.property_list, self.cern, self.pyccda_dictionary)
                self.aux_worker_for_preview_one_device.moveToThread(self.aux_thread_for_preview_one_device)
                self.aux_worker_for_preview_one_device.finished.connect(self.finishThreadPreviewOneDevice)
                self.aux_thread_for_preview_one_device.started.connect(self.aux_worker_for_preview_one_device.start)
                self.aux_thread_for_preview_one_device.start()
                self.aux_worker_for_preview_one_device.processed.connect(self.sendUpdatesWorkingModesPreview)

        return

    #----------------------------------------------#

    # function that re-opens the last window
    def backToLastWindow(self):

        # print the action
        print("{} - Button BACK pressed".format(UI_FILENAME))

        # if you were in settings, go back to main
        if self.current_window == "settings":

            # check you are not in premain
            if self.CEmbeddedDisplay.filename != "":

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device window...", 0)
                self.app.main_window.statusBar().repaint()

                # stop old thread (preview_one_device)
                if type(self.aux_thread_for_preview_one_device) == QThread:
                    if self.aux_thread_for_preview_one_device.isRunning():
                        self.aux_worker_for_preview_one_device.stop()

                # stop old threads (summary)
                were_threads_running = False
                for device in self.acc_device_list_summary:
                    if device in self.working_devices:
                        if device in self.summary_thread_dict.keys():
                            if type(self.summary_thread_dict[device]) == QThread:
                                if self.summary_thread_dict[device].isRunning():
                                    self.summary_worker_dict[device].stop()
                                    were_threads_running = True

                # stop japc subs (summary)
                if were_threads_running:
                    self.japc.stopSubscriptions()
                    self.japc.clearSubscriptions()

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file()

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_freeze.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        # if you were in main, go back to preview
        elif self.current_window == "main":

            # check you are not in premain
            if self.CEmbeddedDisplay.filename != "":

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device preview...", 0)
                self.app.main_window.statusBar().repaint()

                # stop old thread (preview_one_device)
                if type(self.aux_thread_for_preview_one_device) == QThread:
                    if self.aux_thread_for_preview_one_device.isRunning():
                        self.aux_worker_for_preview_one_device.stop()

                # stop old threads (summary)
                were_threads_running = False
                for device in self.acc_device_list_summary:
                    if device in self.working_devices:
                        if device in self.summary_thread_dict.keys():
                            if type(self.summary_thread_dict[device]) == QThread:
                                if self.summary_thread_dict[device].isRunning():
                                    self.summary_worker_dict[device].stop()
                                    were_threads_running = True

                # stop japc subs (summary)
                if were_threads_running:
                    self.japc.stopSubscriptions()
                    self.japc.clearSubscriptions()

                # clear for new device
                if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates")):
                    shutil.rmtree(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates"))

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "preview_one_device.py"
                self.CEmbeddedDisplay.open_file()

                # thread for preview only if device is working
                if self.current_device in self.working_devices:

                    # get the property list
                    self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())

                    # order the property list
                    self.property_list.sort()

                    # recheck if the modes are working each x seconds
                    self.aux_thread_for_preview_one_device = QThread(parent=self)
                    self.aux_worker_for_preview_one_device = workingModesThreadWorkerPreview(self.current_device, self.current_accelerator, self.japc, self.property_list, self.cern, self.pyccda_dictionary)
                    self.aux_worker_for_preview_one_device.moveToThread(self.aux_thread_for_preview_one_device)
                    self.aux_worker_for_preview_one_device.finished.connect(self.finishThreadPreviewOneDevice)
                    self.aux_thread_for_preview_one_device.started.connect(self.aux_worker_for_preview_one_device.start)
                    self.aux_thread_for_preview_one_device.start()

                    # update once the thread outputs the results
                    self.aux_worker_for_preview_one_device.processed.connect(self.sendUpdatesWorkingModesPreview)

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_freeze.setEnabled(False)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(False)

                # update the current window
                self.current_window = "preview"

        return

    #----------------------------------------------#

    # function that checks if the OPEN DEVICE button was pressed and open the device in case it was
    def isOpenDevicePushButtonPressed(self):

        # check if txt exists
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt")):

            # init the boolean
            wasTheButtonPressed = "False"

            # open it
            with open(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt"), "r") as f:
                wasTheButtonPressed = f.read()

            # if the button was pressed then open the device panel
            if wasTheButtonPressed == "True":

                # remove the file because we already know we have to open the device
                os.remove(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt"))

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device window...", 0)
                self.app.main_window.statusBar().repaint()

                # stop old thread (preview_one_device)
                if type(self.aux_thread_for_preview_one_device) == QThread:
                    if self.aux_thread_for_preview_one_device.isRunning():
                        self.aux_worker_for_preview_one_device.stop()

                # stop old threads (summary)
                were_threads_running = False
                for device in self.acc_device_list_summary:
                    if device in self.working_devices:
                        if device in self.summary_thread_dict.keys():
                            if type(self.summary_thread_dict[device]) == QThread:
                                if self.summary_thread_dict[device].isRunning():
                                    self.summary_worker_dict[device].stop()
                                    were_threads_running = True

                # stop japc subs (summary)
                if were_threads_running:
                    self.japc.stopSubscriptions()
                    self.japc.clearSubscriptions()

                # open main container
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file()

                # enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_freeze.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        return

    #----------------------------------------------#

    # function that writes the selector (for Settings)
    def writeSelectorIntoTxt(self):

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # write the selector
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt"), "w") as f:
            f.write(str(self.current_selector))

        return

    #----------------------------------------------#

    # function that writes the device name into a txt file
    def writeDeviceIntoTxtForSubWindows(self, acc_name):

        # get accelerator specific devices
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == acc_name])

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # write the current device
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt"), "w") as f:
            f.write(str(self.current_device))

        # write the current accelerator
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt"), "w") as f:
            f.write(str(acc_name))

        # write the exception of the current device
        with open(os.path.join(self.app_temp_dir, "aux_txts", "exception_premain.txt"), "w") as f:
            f.write("{}\n".format(self.exception_dict[str(self.current_device)]))

        # write the file: device_list_premain
        with open(os.path.join(self.app_temp_dir, "aux_txts", "device_list_premain.txt"), "w") as f:
            for dev in acc_device_list:
                f.write("{}\n".format(dev))

        # write the file: working_devices_premain
        with open(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt"), "w") as f:
            for dev in self.working_devices:
                f.write("{}\n".format(dev))

        # write the preloaded devices
        with open(os.path.join(self.app_temp_dir, "aux_txts", "preloaded_devices_premain.txt"), "w") as f:
            for dev in list(self.preloaded_devices):
                f.write("{}\n".format(dev))

        return

    #----------------------------------------------#

    # function that writes a file whenever the freeze button is pressed
    def sendFreezeText(self):

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # if it is pressed
        if self.toolButton_freeze.isChecked():

            # change icon
            self.toolButton_freeze.setIcon(QIcon("icons/freezing_2.png"))

            # write the file
            with open(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt"), "w") as f:
                f.write("True")

        # if it is not pressed
        else:

            # change icon
            self.toolButton_freeze.setIcon(QIcon("icons/freezing_1.png"))

            # remove the freeze txt
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt")):
                os.remove(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt"))

        return

    #----------------------------------------------#

    # function that writes the mode updates to an aux json file
    def sendUpdatesWorkingModesPreview(self, modules_data, errors):

        # create the saving dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates"))

        # write the file: modules_data_for_preview_one_device
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_for_preview_one_device.json"), "w") as fp:
            json.dump(modules_data, fp, sort_keys=True, indent=4)

        # write the file: errors_for_preview_one_device
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_for_preview_one_device.json"), "w") as fp:
            json.dump(errors, fp, sort_keys=True, indent=4)

        return

    #----------------------------------------------#

    # function that writes the mode updates to an aux json file
    def sendUpdatesWorkingModesSummary(self, modules_data, errors, current_device):

        # create the saving dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates"))

        # write the file
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "modules_data_{}.json".format(current_device)), "w") as fp:
            json.dump(modules_data, fp, sort_keys=True, indent=4)

        # write the file
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "thread_device_updates", "errors_{}.json".format(current_device)), "w") as fp:
            json.dump(errors, fp, sort_keys=True, indent=4)

        return

    #----------------------------------------------#

    # function that does all operations that are required after comrad is fully loaded
    def doOperationsAfterComradIsFullyLoaded(self):

        # click the root and stop the timer when comrad is fully loaded
        if self.is_comrad_fully_loaded:

            # click the root
            self.selectAndClickTheRoot()

            # change the title of the app
            self.app.main_window.setWindowTitle("DIAMOND BLM EXPERT GUI")

            # change the logo
            self.app.main_window.setWindowIcon(QIcon("icons/diamond_2.png"))

            # hide the log console (not needed when using launcher.py)
            # self.app.main_window.hide_log_console()

            # finally stop the timer
            self.timer_hack_operations_after_comrad_is_fully_loaded.stop()

        return

    #----------------------------------------------#

    # iterator function to iterate over treeview rows
    def iterItems(self, root):
        if root is not None:
            for row in range(root.rowCount()):
                row_item = root.child(row, 0)
                if row_item.hasChildren():
                    for childIndex in range(row_item.rowCount()):
                        child = row_item.child(childIndex, 0)
                        yield child

    #----------------------------------------------#

########################################################
########################################################