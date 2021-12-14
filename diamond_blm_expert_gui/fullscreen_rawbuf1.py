########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CContextFrame, CCommandButton, CApplication, CValueAggregator, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QBrush, QPixmap, QFont, QDoubleValidator, QIntValidator)
from PyQt5.QtCore import (QSize, Qt, QTimer, QThread, pyqtSignal, QObject, QEventLoop, QCoreApplication, QRect, QAbstractTableModel)
from PyQt5.QtWidgets import (QSplitter, QLineEdit, QHeaderView, QTableView, QGroupBox, QSpacerItem, QFrame, QSizePolicy, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget, QProgressDialog, QScrollArea, QPushButton, QAbstractItemView, QAbstractScrollArea)
from PyQt5.Qt import QItemSelectionModel, QMenu
import pyqtgraph as pg
import pyjapc

# OTHER IMPORTS

import sys
import os
import time
import numpy as np
import math
from general_utils import createCustomTempDir, getSystemTempDir
import json

########################################################
########################################################

# GLOBALS

# ui file
UI_FILENAME = "fullscreen_rawbuf1.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"

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
        self.sync_wrt_main = False

        # set current device
        self.current_device = "SP.BA2.BLMDIAMOND.2"
        self.LoadDeviceFromTxt()

        # retrieve the pyccda json info file
        self.readPyCCDAJsonFile()

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # aux variable for the after-fully-loaded-comrad operations
        self.is_comrad_fully_loaded = False

        # status bar message
        self.app.main_window.statusBar().showMessage("Successfully opened window for {}!".format(self.current_device), 30*1000)
        self.app.main_window.statusBar().repaint()

        # create japc object
        self.japc = pyjapc.PyJapc()

        # load the file
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("rawBuf1 - {}".format(self.current_device))

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

        # pyqtgraph plot for rabuf1
        self.verticalLayout_Capture.removeItem(self.horizontalLayout)
        self.plot_rawbuf1 = pg.PlotWidget(title="rawBuf1")
        self.plot_rawbuf1.getPlotItem().enableAutoRange()
        self.plot_rawbuf1.getPlotItem().setAutoVisible()
        # self.plot_rawbuf1.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf1.getPlotItem().showButtons()
        self.plot_rawbuf1.getPlotItem().showGrid(x=False, y=False, alpha=0.3)
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

        # splitter to separate both panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.frame_left)
        self.splitter.addWidget(self.frame_right)
        self.splitter.setHandleWidth(0)
        self.splitter.setStretchFactor(0, 80)
        self.splitter.setStretchFactor(1, 20)
        # self.splitter.setStyleSheet("QSplitter::handle { background-color: rgb(200,200,200);}")
        self.horizontalLayout_frame_after_main_form.addWidget(self.splitter)

        # add a spacer
        spacerItem_1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.verticalLayout_phasing.addItem(spacerItem_1)

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # groupbox for Zooming
        self.groupbox_zooming = QGroupBox(self.frame_phasing)
        self.groupbox_zooming.setObjectName("groupBox_Zooming")
        self.groupbox_zooming.setAlignment(Qt.AlignCenter)
        self.groupbox_zooming.setFlat(True)
        self.groupbox_zooming.setCheckable(False)
        self.groupbox_zooming.setTitle("Zooming")
        self.groupbox_zooming.setFont(font_for_groupbox)
        self.verticalLayout_phasing.addWidget(self.groupbox_zooming)

        # layout for zooming
        self.gridLayout_zooming = QGridLayout(self.groupbox_zooming)
        self.gridLayout_zooming.setObjectName("gridLayout_Zooming")

        # lineedits row 1
        self.lineEdit_from_microseconds = QLineEdit(self.groupbox_zooming)
        self.lineEdit_from_microseconds.setAlignment(Qt.AlignCenter)
        self.lineEdit_from_microseconds.setPlaceholderText("from (microseconds)")
        self.lineEdit_from_microseconds.setObjectName("lineEdit_from_microseconds")
        self.lineEdit_from_microseconds.setStyleSheet("QLineEdit{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_from_microseconds, 0, 0, 1, 1)
        self.lineEdit_to_microseconds = QLineEdit(self.groupbox_zooming)
        self.lineEdit_to_microseconds.setAlignment(Qt.AlignCenter)
        self.lineEdit_to_microseconds.setPlaceholderText("to (microseconds)")
        self.lineEdit_to_microseconds.setObjectName("lineEdit_to_microseconds")
        self.lineEdit_to_microseconds.setStyleSheet("QLineEdit{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_to_microseconds, 0, 1, 1, 1)
        self.pushButton_microseconds = QPushButton(self.groupbox_zooming)
        self.pushButton_microseconds.setObjectName("pushButton_microseconds")
        self.pushButton_microseconds.setText("Apply")
        self.pushButton_microseconds.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 4px;\n"
                                          "    padding-bottom: 4px;\n"
                                          "    padding-left: 6px;\n"
                                          "    padding-right: 6px;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:focus{\n"
                                          "    outline: none;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.pushButton_microseconds, 0, 2, 1, 1)

        # lineedits row 2
        self.lineEdit_from_turns = QLineEdit(self.groupbox_zooming)
        self.lineEdit_from_turns.setAlignment(Qt.AlignCenter)
        self.lineEdit_from_turns.setPlaceholderText("from (turns)")
        self.lineEdit_from_turns.setObjectName("lineEdit_from_turns")
        self.lineEdit_from_turns.setStyleSheet("QLineEdit{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_from_turns, 1, 0, 1, 1)
        self.lineEdit_to_turns = QLineEdit(self.groupbox_zooming)
        self.lineEdit_to_turns.setAlignment(Qt.AlignCenter)
        self.lineEdit_to_turns.setPlaceholderText("to (turns)")
        self.lineEdit_to_turns.setObjectName("lineEdit_to_turns")
        self.lineEdit_to_turns.setStyleSheet("QLineEdit{\n" 
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_to_turns, 1, 1, 1, 1)
        self.pushButton_turns = QPushButton(self.groupbox_zooming)
        self.pushButton_turns.setObjectName("pushButton_turns")
        self.pushButton_turns.setText("Apply")
        self.pushButton_turns.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 4px;\n"
                                          "    padding-bottom: 4px;\n"
                                          "    padding-left: 6px;\n"
                                          "    padding-right: 6px;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:focus{\n"
                                          "    outline: none;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.pushButton_turns, 1, 2, 1, 1)

        # lineedits row 3
        self.lineEdit_from_bunchs = QLineEdit(self.groupbox_zooming)
        self.lineEdit_from_bunchs.setAlignment(Qt.AlignCenter)
        self.lineEdit_from_bunchs.setPlaceholderText("from (bunchs)")
        self.lineEdit_from_bunchs.setObjectName("lineEdit_from_bunchs")
        self.lineEdit_from_bunchs.setStyleSheet("QLineEdit{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_from_bunchs, 2, 0, 1, 1)
        self.lineEdit_to_bunchs = QLineEdit(self.groupbox_zooming)
        self.lineEdit_to_bunchs.setAlignment(Qt.AlignCenter)
        self.lineEdit_to_bunchs.setPlaceholderText("to (bunchs)")
        self.lineEdit_to_bunchs.setObjectName("lineEdit_to_bunchs")
        self.lineEdit_to_bunchs.setStyleSheet("QLineEdit{\n" 
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.lineEdit_to_bunchs, 2, 1, 1, 1)
        self.pushButton_bunchs = QPushButton(self.groupbox_zooming)
        self.pushButton_bunchs.setObjectName("pushButton_bunchs")
        self.pushButton_bunchs.setText("Apply")
        self.pushButton_bunchs.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 4px;\n"
                                          "    padding-bottom: 4px;\n"
                                          "    padding-left: 6px;\n"
                                          "    padding-right: 6px;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:focus{\n"
                                          "    outline: none;\n"
                                          "}\n"
                                          "\n"
                                          "QPushButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.gridLayout_zooming.addWidget(self.pushButton_bunchs, 2, 2, 1, 1)

        # context frame of the groupbox
        self.CContextFrame_Commands = CContextFrame(self.frame_phasing)
        self.CContextFrame_Commands.setObjectName("CContextFrame_Commands")
        self.CContextFrame_Commands.inheritSelector = False
        self.CContextFrame_Commands.selector = ""

        # layout of the context frame (0 margin)
        self.layoutContextFrame = QVBoxLayout(self.CContextFrame_Commands)
        self.layoutContextFrame.setObjectName("layoutContextFrame")
        self.layoutContextFrame.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_phasing.addWidget(self.CContextFrame_Commands)

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # groupbox for Commands
        self.groupbox_commands = QGroupBox(self.CContextFrame_Commands)
        self.groupbox_commands.setObjectName("groupBox_Commands")
        self.groupbox_commands.setAlignment(Qt.AlignCenter)
        self.groupbox_commands.setFlat(True)
        self.groupbox_commands.setCheckable(False)
        self.groupbox_commands.setTitle("Commands")
        self.groupbox_commands.setFont(font_for_groupbox)
        self.layoutContextFrame.addWidget(self.groupbox_commands)

        # groupbox layout
        self.layout_groupbox_commands = QGridLayout(self.groupbox_commands)
        self.layout_groupbox_commands.setObjectName("layout_groupBox_Commands")

        # commands
        self.ccommandbutton_1 = CCommandButton(self.groupbox_commands)
        icon = QIcon()
        # icon.addPixmap(QPixmap(SAVING_PATH + "/icons/command.png"), QIcon.Normal, QIcon.Off)
        self.ccommandbutton_1.setIcon(icon)
        self.ccommandbutton_1.setAutoDefault(False)
        self.ccommandbutton_1.setDefault(False)
        self.ccommandbutton_1.setFlat(False)
        self.ccommandbutton_1.setProperty("channel", "{}/{}".format(self.current_device, "TriggerCapture"))
        self.ccommandbutton_1.setObjectName("ccommandbutton_1")
        self.ccommandbutton_1.setText("TriggerCapture")
        self.ccommandbutton_1.setMinimumSize(QSize(0, 25))
        self.ccommandbutton_1.setStyleSheet("CCommandButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    margin-left: 12px;\n"
                                          "    margin-right: 12px;\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "}\n"
                                          "\n"
                                          "CCommandButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "CCommandButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.layout_groupbox_commands.addWidget(self.ccommandbutton_1)

        # commands
        self.ccommandbutton_2 = CCommandButton(self.groupbox_commands)
        icon = QIcon()
        # icon.addPixmap(QPixmap(SAVING_PATH + "/icons/command.png"), QIcon.Normal, QIcon.Off)
        self.ccommandbutton_2.setIcon(icon)
        self.ccommandbutton_2.setAutoDefault(False)
        self.ccommandbutton_2.setDefault(False)
        self.ccommandbutton_2.setFlat(False)
        self.ccommandbutton_2.setProperty("channel", "{}/{}".format(self.current_device, "ResetCapture"))
        self.ccommandbutton_2.setObjectName("ccommandbutton_2")
        self.ccommandbutton_2.setText("ResetCapture")
        self.ccommandbutton_2.setMinimumSize(QSize(0, 25))
        self.ccommandbutton_2.setStyleSheet("CCommandButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    margin-left: 12px;\n"
                                          "    margin-right: 12px;\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "}\n"
                                          "\n"
                                          "CCommandButton:hover{\n"
                                          "    background-color: rgb(230, 230, 230);\n"
                                          "}\n"
                                          "\n"
                                          "CCommandButton:pressed{\n"
                                          "    background-color: rgb(200, 200, 200);\n"
                                          "}")
        self.layout_groupbox_commands.addWidget(self.ccommandbutton_2)

        # update groupbox size in function of the number of rows
        # self.groupbox_commands.setFixedHeight(int(20 * (2 + 2)))

        # init data list
        self.data_model_expert_setting = []

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # groupbox for ExpertSetting
        self.groupbox_expert_setting = QGroupBox(self.frame_phasing)
        self.groupbox_expert_setting.setObjectName("groupBox_ExpertSetting")
        self.groupbox_expert_setting.setAlignment(Qt.AlignCenter)
        self.groupbox_expert_setting.setFlat(True)
        self.groupbox_expert_setting.setCheckable(False)
        self.groupbox_expert_setting.setTitle("ExpertSetting")
        self.groupbox_expert_setting.setFont(font_for_groupbox)
        self.verticalLayout_phasing.addWidget(self.groupbox_expert_setting)

        # groupbox layout
        self.layout_groupbox_expert_setting = QGridLayout(self.groupbox_expert_setting)
        self.layout_groupbox_expert_setting.setObjectName("layout_groupBox_ExpertSetting")

        # create table
        self.table_expert_setting = QTableView(self.groupbox_expert_setting)
        self.table_expert_setting.setStyleSheet("QTableView{\n"
                                                   "    background-color: rgb(243, 243, 243);\n"
                                                   "    margin-top: 0;\n"
                                                   "}")
        self.table_expert_setting.setFrameShape(QFrame.StyledPanel)
        self.table_expert_setting.setFrameShadow(QFrame.Plain)
        self.table_expert_setting.setDragEnabled(False)
        self.table_expert_setting.setAlternatingRowColors(True)
        self.table_expert_setting.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_expert_setting.setShowGrid(True)
        self.table_expert_setting.setGridStyle(Qt.SolidLine)
        self.table_expert_setting.setObjectName("tableView_ExpertSetting")
        self.table_expert_setting.horizontalHeader().setVisible(True)
        self.table_expert_setting.horizontalHeader().setHighlightSections(False)
        self.table_expert_setting.horizontalHeader().setDefaultSectionSize(0)
        self.table_expert_setting.horizontalHeader().setMinimumSectionSize(0)
        self.table_expert_setting.horizontalHeader().setStretchLastSection(True)
        self.table_expert_setting.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table_expert_setting.verticalHeader().setVisible(False)
        self.table_expert_setting.verticalHeader().setDefaultSectionSize(30)
        self.table_expert_setting.verticalHeader().setHighlightSections(False)
        self.table_expert_setting.verticalHeader().setMinimumSectionSize(30)
        self.table_expert_setting.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_expert_setting.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_expert_setting.setFocusPolicy(Qt.NoFocus)
        self.table_expert_setting.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_expert_setting.horizontalHeader().setFixedHeight(30)
        self.table_expert_setting.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.table_expert_setting.show()
        self.layout_groupbox_expert_setting.addWidget(self.table_expert_setting)

        # fill table
        for field in ["FBDEPTH", "FBEXTRADEPTH0", "FBEXTRADEPTH0", "SYNCDELDEPTH"]:
            try:
                data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(self.current_device, "ExpertSetting", field), timingSelectorOverride="", getHeader=False, noPyConversion=False)
            except Exception as xcp:
                data_from_pyjapc = "-"
            self.data_model_expert_setting.append([str(field), str(data_from_pyjapc), str(data_from_pyjapc)])

        # update model
        self.data_table_model_expert_setting = TableModel(data=self.data_model_expert_setting, header_labels=["Field", "Old Value", "New Value"], three_column_window=True)
        self.table_expert_setting.setModel(self.data_table_model_expert_setting)
        self.table_expert_setting.update()

        # update groupbox size in function of the number of rows
        self.groupbox_expert_setting.setFixedHeight(int(36 * (len(self.data_model_expert_setting) + 2)))

        # frame for get and set buttons
        self.frame_get_set = QFrame(self)
        self.frame_get_set.setFrameShape(QFrame.NoFrame)
        self.frame_get_set.setFrameShadow(QFrame.Plain)
        self.frame_get_set.setObjectName("frame_get_set")
        self.horizontalLayout_get_set = QHBoxLayout(self.frame_get_set)
        self.horizontalLayout_get_set.setContentsMargins(120, 0, 120, 0)
        self.horizontalLayout_get_set.setSpacing(6)
        self.horizontalLayout_get_set.setObjectName("horizontalLayout_get_set")
        self.pushButton_get = QPushButton(self.frame_get_set)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_get.sizePolicy().hasHeightForWidth())
        self.pushButton_get.setSizePolicy(sizePolicy)
        self.pushButton_get.setMinimumSize(QSize(60, 32))
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
        self.pushButton_get.setText("GET")
        self.horizontalLayout_get_set.addWidget(self.pushButton_get)
        self.pushButton_set = QPushButton(self.frame_get_set)
        self.pushButton_set.setMinimumSize(QSize(60, 32))
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
        self.pushButton_set.setText("SET")
        self.horizontalLayout_get_set.addWidget(self.pushButton_set)
        self.verticalLayout_phasing.addWidget(self.frame_get_set)

        # add a spacer
        spacerItem_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.verticalLayout_phasing.addItem(spacerItem_2)

        return

    #----------------------------------------------#

    # function that retrieves and displays the values of the fields
    def getFunction(self, show_message = False):

        # print the GET action
        print("{} - Button GET pressed".format(UI_FILENAME))

        # init data list
        self.data_model_expert_setting = []

        # fill table
        for field in ["FBDEPTH", "FBEXTRADEPTH0", "FBEXTRADEPTH0", "SYNCDELDEPTH"]:
            try:
                data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(self.current_device, "ExpertSetting", field), timingSelectorOverride="", getHeader=False, noPyConversion=False)
            except:
                data_from_pyjapc = "-"
            self.data_model_expert_setting.append([str(field), str(data_from_pyjapc), str(data_from_pyjapc)])

        # update model
        self.data_table_model_expert_setting = TableModel(data=self.data_model_expert_setting, header_labels=["Field", "Old Value", "New Value"], three_column_window=True)
        self.table_expert_setting.setModel(self.data_table_model_expert_setting)
        self.table_expert_setting.update()

        # update groupbox size in function of the number of rows
        self.groupbox_expert_setting.setFixedHeight(int(36 * (len(self.data_model_expert_setting) + 2)))

        # status bar message
        if show_message:
            self.app.main_window.statusBar().showMessage("Command GET ran successfully!", 3*1000)
            self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET pressed".format(UI_FILENAME))

        # boolean
        types_are_wrong = False

        # init the boolean
        areAllFieldsJustTheSame = True

        # create dictionary to inject
        dict_to_inject = self.japc.getParam("{}/{}".format(self.current_device, "ExpertSetting"), timingSelectorOverride="", getHeader=False, noPyConversion=False)

        # iterate over table
        for row_values in self.data_model_expert_setting:

            # retrieve values
            field = row_values[0]
            old_value = row_values[1]
            new_value = row_values[2]

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

            # inject the value
            dict_to_inject["{}".format(field)] = new_value

        # do the SET
        if not areAllFieldsJustTheSame:
            self.japc.setParam("{}/{}".format(self.current_device, "ExpertSetting"), dict_to_inject, timingSelectorOverride="")

        # update values in the table
        self.getFunction(show_message = False)

        # status bar message
        self.app.main_window.statusBar().showMessage("Command SET ran successfully!", 3*1000)
        self.app.main_window.statusBar().repaint()

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

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        # checkbox for flags 1 and 2
        self.checkBox_bunch.stateChanged.connect(self.updateFlags_1_2)

        # checkbox for flags 5 and 6
        self.checkBox_turn.stateChanged.connect(self.updateFlags_5_6)

        # disable buttons until reception of data
        self.checkBox_bunch.setEnabled(False)
        self.checkBox_turn.setEnabled(False)
        self.checkBox_bst.setEnabled(False)
        self.checkBox_sync_main.setEnabled(False)
        self.groupbox_zooming.setEnabled(False)

        # checkbox for sync signal
        self.checkBox_sync_main.stateChanged.connect(self.syncWithMainWindowFunction)
        # self.checkBox_sync_main.hide()
        self.checkBox_sync_main.setToolTip("This checkbox synchronizes the buffer plots of the main and fullscreen panels so that the received data is plotted simultaneously in both windows."
                                           " It is usually required to compensate for the waiting times that UCAP imposes on the main window."
                                           " For example, if it is checked and the freezing option is enabled in the main window, none of the plots will be updated to new values."
                                           " When unchecked, data will be plotted as soon as it is received no matter what the current plot is shown in the main, which can be convenient when adjusting the phase of the signal or when using the TriggerCapture and ResetCapture commands.")

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

        # getters
        self.pushButton_get.clicked.connect(lambda: self.getFunction(show_message = True))

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        # commands
        self.ccommandbutton_1.clicked.connect(self.commandClicked)
        self.ccommandbutton_2.clicked.connect(self.commandClicked)

        # zooming
        self.pushButton_microseconds.clicked.connect(self.pushButtonZoomingMicroClicked)
        self.pushButton_turns.clicked.connect(self.pushButtonZoomingTurnsClicked)
        self.pushButton_bunchs.clicked.connect(self.pushButtonZoomingBunchsClicked)

        return

    #----------------------------------------------#

    # function to set the axis range
    def pushButtonZoomingMicroClicked(self):

        # check we have data
        if self.bufferFirstPlotsPainted:

            # check line edits are not empty
            if self.lineEdit_from_microseconds.text() and self.lineEdit_to_microseconds.text():

                # get lower and upper limit
                lower_limit = self.lineEdit_from_microseconds.text()
                upper_limit = self.lineEdit_to_microseconds.text()
                lower_limit = float(lower_limit.replace(",", "."))
                upper_limit = float(upper_limit.replace(",", "."))

                # set range
                self.plot_rawbuf1.setXRange(lower_limit, upper_limit, padding=0)

        return

    #----------------------------------------------#

    # function to set the axis range
    def pushButtonZoomingBunchsClicked(self):

        # check we have data
        if self.bufferFirstPlotsPainted:

            # check line edits are not empty
            if self.lineEdit_from_bunchs.text() and self.lineEdit_to_bunchs.text():

                # get lower and upper limit
                lower_limit = self.lineEdit_from_bunchs.text()
                upper_limit = self.lineEdit_to_bunchs.text()
                lower_limit = int(lower_limit.replace(",", "."))
                upper_limit = int(upper_limit.replace(",", "."))

                # get the real bunch limits
                if lower_limit == 0:
                    bunchs_lower_limit = 0
                elif lower_limit >= 1 and lower_limit <= len(self.idx_flags_one_two):
                    bunchs_lower_limit = self.time_vector[self.idx_flags_one_two[lower_limit - 1]]
                elif lower_limit > len(self.idx_flags_one_two):
                    bunchs_lower_limit = self.time_vector[-1]
                if upper_limit == 0:
                    bunchs_upper_limit = 0
                elif upper_limit >= 1 and upper_limit <= len(self.idx_flags_one_two):
                    bunchs_upper_limit = self.time_vector[self.idx_flags_one_two[upper_limit - 1]]
                elif upper_limit > len(self.idx_flags_one_two):
                    bunchs_upper_limit = self.time_vector[-1]

                # set range
                self.plot_rawbuf1.setXRange(bunchs_lower_limit, bunchs_upper_limit, padding=0)

        return

    #----------------------------------------------#

    # function to set the axis range
    def pushButtonZoomingTurnsClicked(self):

        # check we have data
        if self.bufferFirstPlotsPainted:

            # check line edits are not empty
            if self.lineEdit_from_turns.text() and self.lineEdit_to_turns.text():

                # get lower and upper limit
                lower_limit = self.lineEdit_from_turns.text()
                upper_limit = self.lineEdit_to_turns.text()
                lower_limit = int(lower_limit.replace(",", "."))
                upper_limit = int(upper_limit.replace(",", "."))

                # get the real turn limits
                if lower_limit == 0:
                    turns_lower_limit = 0
                elif lower_limit >= 1 and lower_limit <= len(self.inf_lines_pos_1):
                    turns_lower_limit = self.inf_lines_pos_1[lower_limit - 1]
                elif lower_limit > len(self.inf_lines_pos_1):
                    turns_lower_limit = self.time_vector[-1]
                if upper_limit == 0:
                    turns_upper_limit = 0
                elif upper_limit >= 1 and upper_limit <= len(self.inf_lines_pos_1):
                    turns_upper_limit = self.inf_lines_pos_1[upper_limit - 1]
                elif upper_limit > len(self.inf_lines_pos_1):
                    turns_upper_limit = self.time_vector[-1]

                # set range
                self.plot_rawbuf1.setXRange(turns_lower_limit, turns_upper_limit, padding=0)

        return

    #----------------------------------------------#

    # function to handle command clicks
    def commandClicked(self):

        # status bar message
        self.app.main_window.statusBar().showMessage("Command clicked!", 3*1000)
        self.app.main_window.statusBar().repaint()

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
            self.time_vector = np.linspace(0, (len(self.data_rawBuf1) - 1) * (1 / (Fs * 1000)), num=len(self.data_rawBuf1))
            self.compute_time_vector_first_time = False

        # get only bunch flags (1 and 2) for buf1
        idx_flags_one_two = np.where((self.data_rawBufFlags1 == 1) | (self.data_rawBufFlags1 == 2))[0]
        flags_one_two = np.zeros(self.data_rawBufFlags1.shape)
        flags_one_two[idx_flags_one_two] = 1

        # save bunch idx for the zooming options
        self.idx_flags_one_two = idx_flags_one_two

        # get only turn flags (5 and 6) for buf1
        idx_flags_five_six = np.where((self.data_rawBufFlags1 == 5) | (self.data_rawBufFlags1 == 6))[0]
        flags_five_six = np.zeros(self.data_rawBufFlags1.shape)
        flags_five_six[idx_flags_five_six] = 1
        self.inf_lines_pos_1 = self.time_vector[idx_flags_five_six]

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
                # self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                for line_pos in self.inf_lines_pos_1:
                    infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                    self.plot_rawbuf1.addItem(infinite_line)
            self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
            self.plot_rawbuf1.show()

            # set cycle information
            self.CLabel_acqStamp_Capture.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
            self.CLabel_cycleName_Capture.setText("<b>cycleName:</b> {}".format(self.data_cycleName))

        # update first plot boolean
        self.bufferFirstPlotsPainted = True

        # enable buttons
        self.checkBox_bunch.setEnabled(True)
        self.checkBox_turn.setEnabled(True)
        self.checkBox_bst.setEnabled(True)
        self.checkBox_sync_main.setEnabled(True)
        self.groupbox_zooming.setEnabled(True)

        # set validators
        self.lineEdit_from_microseconds.setValidator(QDoubleValidator(0, self.time_vector[-1], 4, self, notation=QDoubleValidator.StandardNotation))
        self.lineEdit_to_microseconds.setValidator(QDoubleValidator(0, self.time_vector[-1], 4, self, notation=QDoubleValidator.StandardNotation))
        self.lineEdit_from_turns.setValidator(QIntValidator(0, len(self.inf_lines_pos_1)-1, self))
        self.lineEdit_to_turns.setValidator(QIntValidator(0, len(self.inf_lines_pos_1)-1, self))
        self.lineEdit_from_bunchs.setValidator(QIntValidator(0, len(self.idx_flags_one_two)-1, self))
        self.lineEdit_to_bunchs.setValidator(QIntValidator(0, len(self.idx_flags_one_two)-1, self))

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxt(self):

        # load current device
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device.txt"), "r") as f:
                self.current_device = f.read()

        # load current accelerator
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator.txt"), "r") as f:
                self.current_accelerator = f.read()

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
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf1.getPlotItem().clear()
                if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                    self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
                if self.flags_turn1.size != 0 and self.is_turn1_checked:
                    # self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                    for line_pos in self.inf_lines_pos_1:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf1.addItem(infinite_line)
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

        # if not
        else:

            # remove the flags
            print("{} - Bunchs1 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = False
            self.is_bunch1_checked = False
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf1.getPlotItem().clear()
                if self.flags_turn1.size != 0 and self.is_turn1_checked:
                    # self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                    for line_pos in self.inf_lines_pos_1:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf1.addItem(infinite_line)
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
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf1.getPlotItem().clear()
                if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                    self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
                if self.flags_turn1.size != 0 and self.is_turn1_checked:
                    # self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                    for line_pos in self.inf_lines_pos_1:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf1.addItem(infinite_line)
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

        else:

            # remove the flags
            print("{} - Turns1 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["5,6"] = False
            self.is_turn1_checked = False
            self.plot_rawbuf1.getPlotItem().clear()
            if self.bufferFirstPlotsPainted:
                if self.flags_bunch1.size != 0 and self.is_bunch1_checked:
                    self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_bunch1, pen=QColor("#EF476F"), name="rawBuf1_bunch_flags")
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf1.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # read aux txt
    def readAuxBufferFileForFullscreen(self):

        # if you want to sync the main with the fullscreen
        if self.sync_wrt_main:

            # read buffer boolean
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_1.txt")):
                with open(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_1.txt"), "r") as f:
                    self.is_buffer_plotted_in_the_main_window = f.read()

            # call plot function if buffer is plotted in the main window and we received the data
            if self.is_buffer_plotted_in_the_main_window == "True":

                # set the txt to false
                if self.bufferFirstPlotsPainted:
                    with open(os.path.join(self.app_temp_dir, "aux_txts", "is_buffer_plotted_1.txt"), "w") as f:
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
            self.app.main_window.setWindowTitle("rawBuf1 - {}".format(self.current_device))

            # change the logo
            self.app.main_window.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))

            # init GET
            self.getFunction(show_message=False)

            # hide the log console (not needed when using launcher.py)
            # self.app.main_window.hide_log_console()

            # finally stop the timer
            self.timer_hack_operations_after_comrad_is_fully_loaded.stop()

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