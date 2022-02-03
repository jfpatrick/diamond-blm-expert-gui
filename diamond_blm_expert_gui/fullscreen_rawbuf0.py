########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CContextFrame, CCommandButton, CApplication, CValueAggregator, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QBrush, QPixmap, QFont, QDoubleValidator, QIntValidator)
from PyQt5.QtCore import (QSize, Qt, QTimer, QThread, pyqtSignal, QObject, QEventLoop, QCoreApplication, QRect, QAbstractTableModel, QPoint)
from PyQt5.QtWidgets import (QStyledItemDelegate, QComboBox, QSplitter, QLineEdit, QHeaderView, QTableView, QGroupBox, QDialogButtonBox, QSpacerItem, QFrame, QSizePolicy, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget, QProgressDialog, QScrollArea, QPushButton, QAbstractItemView, QAbstractScrollArea)
from PyQt5.Qt import QItemSelectionModel, QMenu, QPalette
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
from scipy.interpolate import interp1d
from copy import deepcopy

########################################################
########################################################

import socket

temp_system_dir = getSystemTempDir()
with open(os.path.join(temp_system_dir, 'free_ports.txt')) as f:
    free_port_list = f.readlines()

socket_object = socket.socket()
host = socket.gethostname()
free_port = int(free_port_list[1])
try:
    socket_object.bind((host, free_port))
except OSError as xcp:
    print("[{}] A fullscreen window for rawbuf0 is already running on another instance. Please, make sure only one instance is running at the same time. Otherwise, it won't open properly.".format(free_port))
    sys.exit(0)

########################################################
########################################################

# GLOBALS

# get real path
REAL_PATH = os.path.realpath(os.path.dirname(__file__))

# ui file
UI_FILENAME = "fullscreen_rawbuf0.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"

########################################################
########################################################

# peak detector
def thresholding_algo(y, lag, threshold, influence):

    signals = np.zeros(len(y))
    filteredY = np.array(y)
    avgFilter = [0] * len(y)
    stdFilter = [0] * len(y)
    avgFilter[lag - 1] = np.mean(y[0:lag])
    stdFilter[lag - 1] = np.std(y[0:lag])

    for i in range(lag, len(y)):

        if abs(y[i] - avgFilter[i - 1]) > threshold * stdFilter[i - 1]:

            if y[i] > avgFilter[i - 1]:
                signals[i] = 1
            else:
                signals[i] = -1

            filteredY[i] = influence * y[i] + (1 - influence) * filteredY[i - 1]
            avgFilter[i] = np.mean(filteredY[(i - lag + 1):i + 1])
            stdFilter[i] = np.std(filteredY[(i - lag + 1):i + 1])

        else:

            signals[i] = 0
            filteredY[i] = y[i]
            avgFilter[i] = np.mean(filteredY[(i - lag + 1):i + 1])
            stdFilter[i] = np.std(filteredY[(i - lag + 1):i + 1])

    return dict(signals=np.asarray(signals),
                avgFilter=np.asarray(avgFilter),
                stdFilter=np.asarray(stdFilter))

# util function
def can_be_converted_to_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

# util function
def numpy_find_nearest(array, value, side="left"):
    idx = np.searchsorted(array, value, side="left")
    if side=="left":
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
            return array[idx-1], idx-1
        else:
            return array[idx], idx
    elif side=="right":
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
            return array[idx-2], idx-2
        else:
            return array[idx-1], idx-1
    else:
        return None, None

########################################################
########################################################

class DialogWithLineEdit(QDialog):

    #----------------------------------------------#

    # signals
    accepted_boolean = pyqtSignal(bool)

    #----------------------------------------------#

    def __init__(self, parent = None):

        # save the parent
        self.dialog_parent = parent

        # inherit from QDialog
        QDialog.__init__(self, parent)

        # set the window title and build the GUI
        self.setWindowTitle("PhaseAutoTuning Wizard")
        self.buildCodeWidgets()
        self.bindWidgets()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        self.setWindowIcon(QIcon(os.path.join(REAL_PATH, "icons/diamond_2.png")))

        self.resize(420, 160)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QSize(0, 26))
        self.label.setStyleSheet("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.lineEdit = QLineEdit(self)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit.sizePolicy().hasHeightForWidth())
        self.lineEdit.setSizePolicy(sizePolicy)
        self.lineEdit.setMinimumSize(QSize(0, 26))
        self.lineEdit.setStyleSheet("QLineEdit{\n"
                                    "    margin-left: 80px;\n"
                                    "    margin-right: 80px;\n"
                                    "}")
        self.lineEdit.setAlignment(Qt.AlignCenter)
        self.lineEdit.setObjectName("lineEdit")
        self.verticalLayout.addWidget(self.lineEdit)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setMinimumSize(QSize(0, 26))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.label.setText("Please, insert the desired bunch slot in the field below.")
        self.lineEdit.setText("0")

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # buttonbox
        self.buttonBox.accepted.connect(self.accept_function)
        self.buttonBox.rejected.connect(self.reject_function)

        # validator for lineedit
        self.lineEdit.setValidator(QIntValidator(0, 9999999, self))

        return

    #----------------------------------------------#

    def accept_function(self):
        self.accepted_boolean.emit(True)
        return

    def reject_function(self):
        self.accepted_boolean.emit(False)
        return

    #----------------------------------------------#

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels, titles_set_window = False, three_column_window = False, tooltip_list = []):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels = header_labels
        self.titles_set_window = titles_set_window
        self.three_column_window = three_column_window
        self.tooltip_list = tooltip_list

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
            if self.three_column_window and col == 3:
                return QBrush(QColor("#ffffff"))
        elif role == Qt.ToolTipRole:
            if col == 0 or col == 1:
                if self.tooltip_list:
                    return self.tooltip_list[row]

    def rowCount(self, index):

        return len(self._data)

    def columnCount(self, index):

        return len(self._data[0])

    def flags(self, index):

        if index.column() == 3:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):

        if role == Qt.EditRole and index.column() == 3:
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
        self.bct_use_random = False
        self.bct_use_custom = False
        self.bct_from_sps = False
        self.bct_use_received_pattern = False
        self.bct_random_seed = 0
        self.bct_checked = False
        self.y_filling_pattern_not_empty = False
        self.data_bct_save = np.array([0])
        self.counter_of_bct_apply = 0
        self.plotted_bct_at_least_once = False
        self.mouseHoverFirstTime = False
        self.color_indexes_for_combobox = []
        self.old_data_for_autophasing = np.array([])

        # BCT items for the combobox
        self.items_combobox = ["LHC.BCTFR.A6R4.B1", "LHC.BCTFR.A6R4.B2", "RANDOM.SEQUENCE.0", "RANDOM.SEQUENCE.1", "CUSTOM.SEQUENCE.0"]

        # tooltips
        self.tooltip_list = ["FBDEPTH: it delays the data w.r.t. BST on ADC sample steps. Common to both channels.",
                             "SYNCDELDEPTH: it delays the data w.r.t. BST on bunch slot steps. Common to both channels.",
                             "FBEXTRADEPTH0: it allows to delay the skew between channels."]

        # params
        self.list_of_delay_params = ["FBDEPTH", "SYNCDELDEPTH", "FBEXTRADEPTH0"]
        self.list_of_delay_params_user_friendly = ["Thin delay", "Coarse delay", "Thin skew"]
        self.step_list = ["+1.53ns", "-25.0ns", "+1.53ns"]

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
        self.setWindowTitle("rawBuf0 - {}".format(self.current_device))

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

        # set icon stylesheets for checkboxes
        self.checkBox_turn.setStyleSheet("QCheckBox::indicator {\n"
                                            "width: 18px; height: 18px;\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_yellow_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked:pressed {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_pressed_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked:pressed {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_pressed_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked:disabled {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_disabled_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked:disabled {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_disabled_2.png);\n"
                                            "}")
        self.checkBox_bunch.setStyleSheet("QCheckBox::indicator {\n"
                                            "width: 18px; height: 18px;\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_magenta_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked:pressed {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_pressed_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked:pressed {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_pressed_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:checked:disabled {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_true_disabled_2.png);\n"
                                            "}\n"
                                            "QCheckBox::indicator:unchecked:disabled {\n"
                                            rf"image: url({REAL_PATH}/icons/checkbox_false_disabled_2.png);\n"
                                            "}")
        self.checkBox_bct.setStyleSheet("QCheckBox::indicator {\n"
                                          "width: 18px; height: 18px;\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_blue_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_disabled_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_disabled_2.png);\n"
                                          "}")
        self.checkBox_hover.setStyleSheet("QCheckBox::indicator {\n"
                                          "width: 18px; height: 18px;\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_green_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_disabled_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_disabled_2.png);\n"
                                          "}")
        self.checkBox_sync_main.setStyleSheet("QCheckBox::indicator {\n"
                                          "width: 18px; height: 18px;\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_white_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:pressed {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_pressed_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:checked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_true_disabled_2.png);\n"
                                          "}\n"
                                          "QCheckBox::indicator:unchecked:disabled {\n"
                                          rf"image: url({REAL_PATH}/icons/checkbox_false_disabled_2.png);\n"
                                          "}")

        # pyqtgraph plot for rabuf0
        self.verticalLayout_Capture.removeItem(self.horizontalLayout)
        self.plot_rawbuf0 = pg.PlotWidget(title="rawBuf0")
        self.plot_rawbuf0.getPlotItem().enableAutoRange()
        self.plot_rawbuf0.getPlotItem().setAutoVisible()
        # self.plot_rawbuf0.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0.getPlotItem().showButtons()
        self.plot_rawbuf0.getPlotItem().showGrid(x=False, y=False, alpha=0.3)
        self.plot_rawbuf0.getPlotItem().setClipToView(True)
        self.plot_rawbuf0.setDownsampling(auto=True, mode="peak")
        self.plot_rawbuf0.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf0.getPlotItem().setLabel(axis='bottom', text='time (microseconds)')
        # self.plot_rawbuf0.addLegend(horSpacing=20, verSpacing=-5, pen=(255,255,255), frame=True, offset=(-50,-50))
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

        # groupbox for BCT
        self.groupbox_bct = QGroupBox(self.frame_phasing)
        self.groupbox_bct.setObjectName("groupbox_BCT")
        self.groupbox_bct.setAlignment(Qt.AlignCenter)
        self.groupbox_bct.setFlat(True)
        self.groupbox_bct.setCheckable(False)
        self.groupbox_bct.setTitle("BCT")
        self.groupbox_bct.setFont(font_for_groupbox)
        self.verticalLayout_phasing.addWidget(self.groupbox_bct)

        # layout for BCT
        self.gridLayout_bct = QGridLayout(self.groupbox_bct)
        self.gridLayout_bct.setObjectName("gridLayout_BCT")

        # lineedits row 1
        self.comboBox_bct = QComboBox(self.groupbox_bct)
        self.comboBox_bct.setObjectName("comboBox_bct")
        self.comboBox_bct.setToolTip("Use this dropdown to select the desired BCT channel. "
                                     "The BCT devices marked in yellow are selected by default and measure the same beam as the dBLM in question (B1 or B2).")
        self.model_combobox = self.comboBox_bct.model()
        for row in self.items_combobox:
            item_to_append = QStandardItem(str(row))
            self.model_combobox.appendRow(item_to_append)
        self.comboBox_bct.setModel(self.model_combobox)
        self.comboBox_bct.setEditable(True)
        self.comboBox_bct.lineEdit().setAlignment(Qt.AlignCenter)
        self.comboBox_bct.lineEdit().setReadOnly(True)
        self.comboBox_bct.setItemDelegate(QStyledItemDelegate())
        self.comboBox_bct.setStyleSheet("QComboBox{\n"
                                                    "    background-color: rgb(255, 255, 255);\n"
                                                    "    border: 2px solid #A6A6A6;\n"
                                                    "    padding-top: 3px;\n"
                                                    "    padding-bottom: 3px;\n"
                                                    "    padding-left: 0px;\n"
                                                    "    padding-right: 0px;\n"
                                                    "}\n"
                                                    "\n"
                                        "QComboBox::down-arrow{\n"
                                        rf"    image: url({REAL_PATH}/icons/down-arrow.png);\n"
                                        "}\n"
                                        "QComboBox QAbstractItemView{\n"
                                        "    border: 2px solid #A6A6A6;\n"
                                        "    background-color: rgb(255, 255, 255);\n"
                                        "}\n"
                                        "QComboBox QAbstractItemView::item{\n"
                                        "    min-height: 20px;\n"
                                        "}")
        self.gridLayout_bct.addWidget(self.comboBox_bct, 0, 0, 1, 1)
        self.pushButton_comboBox_bct = QPushButton(self.groupbox_bct)
        self.pushButton_comboBox_bct.setObjectName("pushButton_comboBox_bct")
        self.pushButton_comboBox_bct.setText("Apply")
        self.pushButton_comboBox_bct.setStyleSheet("QPushButton{\n"
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
        self.gridLayout_bct.addWidget(self.pushButton_comboBox_bct, 0, 1, 1, 1)

        # lineedits row 2
        self.lineEdit_bct_device_name = QLineEdit(self.groupbox_bct)
        self.lineEdit_bct_device_name.setAlignment(Qt.AlignCenter)
        self.lineEdit_bct_device_name.setPlaceholderText("Insert custom BCT device name...")
        self.lineEdit_bct_device_name.setObjectName("lineEdit_bct_device_name")
        self.lineEdit_bct_device_name.setStyleSheet("QLineEdit{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    border: 2px solid #A6A6A6;\n"
                                          "    padding-top: 3px;\n"
                                          "    padding-bottom: 3px;\n"
                                          "    padding-left: 0px;\n"
                                          "    padding-right: 0px;\n"
                                          "}")
        self.gridLayout_bct.addWidget(self.lineEdit_bct_device_name, 1, 0, 1, 1)
        self.pushButton_bct_device_name = QPushButton(self.groupbox_bct)
        self.pushButton_bct_device_name.setObjectName("pushButton_bct_device_name")
        self.pushButton_bct_device_name.setText("Apply")
        self.pushButton_bct_device_name.setStyleSheet("QPushButton{\n"
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
        self.gridLayout_bct.addWidget(self.pushButton_bct_device_name, 1, 1, 1, 1)

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

        # # test qlabels
        # self.qlabel_microseconds = QLabel(self.groupbox_zooming)
        # self.qlabel_microseconds.setText("Microseconds")
        # self.qlabel_microseconds.setObjectName("qlabel_microseconds")
        # self.qlabel_microseconds.setAlignment(Qt.AlignCenter)
        # self.qlabel_microseconds.setStyleSheet("QLabel{\n"
        #                                   "    background-color: rgb(236, 236, 236);\n"
        #                                   "    border: 2px solid #A6A6A6;\n"
        #                                   "    padding-top: 3px;\n"
        #                                   "    padding-bottom: 3px;\n"
        #                                   "    padding-left: 0px;\n"
        #                                   "    padding-right: 0px;\n"
        #                                   "}")
        # self.gridLayout_zooming.addWidget(self.qlabel_microseconds, 0, 0, 1, 1)

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
        self.pushButton_microseconds_lock = QPushButton(self.groupbox_zooming)
        self.pushButton_microseconds_lock.setObjectName("pushButton_microseconds_lock")
        self.pushButton_microseconds_lock.setText("1")
        self.pushButton_microseconds_lock.setStyleSheet("QPushButton{\n"
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
                                                   "QPushButton:checked{\n"
                                                   "    background-color: rgb(255, 255, 100);\n"
                                                   "}\n"
                                                   "QPushButton:unchecked{\n"
                                                   "    background-color: rgb(255, 255, 255);\n"
                                                   "}\n"
                                                   "\n"
                                                   "QPushButton:pressed{\n"
                                                   "    background-color: rgb(200, 200, 200);\n"
                                                   "}")
        self.pushButton_microseconds_lock.setCheckable(True)
        self.pushButton_microseconds_lock.setChecked(False)
        self.pushButton_microseconds_lock.setToolTip("This button enables the combination mode on the bunch row query. "
                                                     "By pressing it, you can combine microsecond and bunch ranges as if it was an AND operation. For example, "
                                                     "if the microsecond range is (5,10) and the bunch range is (1,3), the resulting zoom will be "
                                                     "a combination of both queries, so it will only show the datapoints belonging to the bunches nº 1,2 and 3, from 5 microseconds onwards.")
        self.gridLayout_zooming.addWidget(self.pushButton_microseconds_lock, 0, 3, 1, 1)

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
        self.pushButton_turns_lock = QPushButton(self.groupbox_zooming)
        self.pushButton_turns_lock.setObjectName("pushButton_turns_lock")
        self.pushButton_turns_lock.setText("2")
        self.pushButton_turns_lock.setStyleSheet("QPushButton{\n"
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
                                                   "QPushButton:checked{\n"
                                                   "    background-color: rgb(255, 255, 100);\n"
                                                   "}\n"
                                                   "QPushButton:unchecked{\n"
                                                   "    background-color: rgb(255, 255, 255);\n"
                                                   "}\n"
                                                   "\n"
                                                   "QPushButton:pressed{\n"
                                                   "    background-color: rgb(200, 200, 200);\n"
                                                   "}")
        self.pushButton_turns_lock.setCheckable(True)
        self.pushButton_turns_lock.setChecked(True)
        self.pushButton_turns_lock.setToolTip("This button enables the combination mode on the bunch row query. "
                                                     "By pressing it, you can combine turn and bunch ranges as if it was an AND operation. For example, "
                                                     "if the turn range is (5,10) and the bunch range is (1,3), the resulting zoom will be "
                                                     "a combination of both queries, so it will only show the datapoints belonging to the bunches nº 1,2 and 3, from the fifth turn onwards.")
        self.gridLayout_zooming.addWidget(self.pushButton_turns_lock, 1, 3, 1, 1)

        # lineedits row 3
        self.lineEdit_from_bunchs = QLineEdit(self.groupbox_zooming)
        self.lineEdit_from_bunchs.setAlignment(Qt.AlignCenter)
        self.lineEdit_from_bunchs.setPlaceholderText("from (bunches)")
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
        self.lineEdit_to_bunchs.setPlaceholderText("to (bunches)")
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
        self.pushButton_bunchs_lock = QPushButton(self.groupbox_zooming)
        self.pushButton_bunchs_lock.setObjectName("pushButton_bunchs_lock")
        self.pushButton_bunchs_lock.setText("2")
        self.pushButton_bunchs_lock.setStyleSheet("QPushButton{\n"
                                                   "    background-color: rgb(255, 255, 100);\n"
                                                   "    border: 2px solid #A6A6A6;\n"
                                                   "    padding-top: 4px;\n"
                                                   "    padding-bottom: 4px;\n"
                                                   "    padding-left: 6px;\n"
                                                   "    padding-right: 6px;\n"
                                                   "}\n"
                                                  "QToolTip{\n"
                                                   "    width: 50px;\n"
                                                   "}\n"
                                                   "\n"
                                                   "QPushButton:focus{\n"
                                                   "    outline: none;\n"
                                                   "}")
        self.pushButton_bunchs_lock.setToolTip("    <html>\n"
                                               "    <div style=\"width: 600px;\">Combination box. If the value is 1, the microsecond range is taken into account for adjusting the zoom interval. If the value is 2, then the turn range is combined with the selected bunch range. By default, turns and bunches are combined at the panel startup.</div>"
                                               "    </html>")
        self.gridLayout_zooming.addWidget(self.pushButton_bunchs_lock, 2, 3, 1, 1)

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
        # icon.addPixmap(QPixmap(os.path.join(REAL_PATH, "icons/command.png")), QIcon.Normal, QIcon.Off)
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
        # icon.addPixmap(QPixmap(os.path.join(REAL_PATH, "icons/command.png")), QIcon.Normal, QIcon.Off)
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

        # commands
        self.ccommandbutton_3 = QPushButton(self.groupbox_commands)
        icon = QIcon()
        # icon.addPixmap(QPixmap(os.path.join(REAL_PATH, "icons/command.png")), QIcon.Normal, QIcon.Off)
        self.ccommandbutton_3.setIcon(icon)
        self.ccommandbutton_3.setAutoDefault(False)
        self.ccommandbutton_3.setDefault(False)
        self.ccommandbutton_3.setFlat(False)
        self.ccommandbutton_3.setObjectName("ccommandbutton_3")
        self.ccommandbutton_3.setText("PhaseAutoTuning")
        self.ccommandbutton_3.setMinimumSize(QSize(0, 25))
        self.ccommandbutton_3.setStyleSheet("QPushButton{\n"
                                          "    background-color: rgb(255, 255, 255);\n"
                                          "    margin-left: 12px;\n"
                                          "    margin-right: 12px;\n"
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
        self.layout_groupbox_commands.addWidget(self.ccommandbutton_3)

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
        self.table_expert_setting.verticalHeader().setDefaultSectionSize(32)
        self.table_expert_setting.verticalHeader().setHighlightSections(False)
        self.table_expert_setting.verticalHeader().setMinimumSectionSize(32)
        self.table_expert_setting.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_expert_setting.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_expert_setting.setFocusPolicy(Qt.NoFocus)
        self.table_expert_setting.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_expert_setting.horizontalHeader().setFixedHeight(30)
        self.table_expert_setting.horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.table_expert_setting.show()
        self.layout_groupbox_expert_setting.addWidget(self.table_expert_setting)

        # fill table
        for field_counter, field in enumerate(self.list_of_delay_params):
            try:
                data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(self.current_device, "ExpertSetting", field), timingSelectorOverride="", getHeader=False, noPyConversion=False)
            except Exception as xcp:
                data_from_pyjapc = "-"
            self.data_model_expert_setting.append([str(self.list_of_delay_params_user_friendly[field_counter]), self.step_list[field_counter], str(data_from_pyjapc), str(data_from_pyjapc)])

        # update model
        self.data_table_model_expert_setting = TableModel(data=self.data_model_expert_setting, header_labels=["BST", "Steps", "Old Value", "New Value"], three_column_window=True, tooltip_list=self.tooltip_list)
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
        for field_counter, field in enumerate(self.list_of_delay_params):
            try:
                data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(self.current_device, "ExpertSetting", field), timingSelectorOverride="", getHeader=False, noPyConversion=False)
            except:
                data_from_pyjapc = "-"
            self.data_model_expert_setting.append([str(self.list_of_delay_params_user_friendly[field_counter]), self.step_list[field_counter], str(data_from_pyjapc), str(data_from_pyjapc)])

        # update model
        self.data_table_model_expert_setting = TableModel(data=self.data_model_expert_setting, header_labels=["BST", "Steps", "Old Value", "New Value"], three_column_window=True, tooltip_list=self.tooltip_list)
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
        for row_counter, row_values in enumerate(self.data_model_expert_setting):

            # retrieve values
            field = self.list_of_delay_params[row_counter]
            old_value = row_values[-2]
            new_value = row_values[-1]

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

        # checkbox for bct
        self.checkBox_bct.stateChanged.connect(self.updateBCTPlot)

        # disable buttons until reception of data
        self.checkBox_bunch.setEnabled(False)
        self.checkBox_turn.setEnabled(False)
        self.checkBox_bct.setEnabled(False)
        self.checkBox_hover.setEnabled(False)
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
        self.ccommandbutton_3.clicked.connect(self.phaseAutoTuning)

        # zooming
        self.pushButton_microseconds.clicked.connect(self.pushButtonZoomingMicroClicked)
        self.pushButton_turns.clicked.connect(self.pushButtonZoomingTurnsClicked)
        self.pushButton_bunchs.clicked.connect(self.pushButtonZoomingBunchsClicked)

        # zooming locking
        self.pushButton_microseconds_lock.clicked.connect(self.lockMicroseconds)
        self.pushButton_turns_lock.clicked.connect(self.lockTurns)

        # bct
        self.pushButton_bct_device_name.clicked.connect(lambda: self.pushButtonApplyBCT("lineedit"))
        self.pushButton_comboBox_bct.clicked.connect(lambda: self.pushButtonApplyBCT("combobox"))
        self.comboBox_bct.currentIndexChanged.connect(self.changedComboboxSelection)

        # hover
        self.checkBox_hover.clicked.connect(self.clearDatapointsFromHover)

        return

    #----------------------------------------------#

    # function to solely change the colors of the combobox
    def changedComboboxSelection(self, index):

        if self.color_indexes_for_combobox:
            if index in self.color_indexes_for_combobox:
                self.comboBox_bct.setStyleSheet("QComboBox{\n"
                                                "    background-color: #ffff66;\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    padding-top: 3px;\n"
                                                "    padding-bottom: 3px;\n"
                                                "    padding-left: 0px;\n"
                                                "    padding-right: 0px;\n"
                                                "}\n"
                                                "\n"
                                                "QComboBox::down-arrow{\n"
                                                rf"    image: url({REAL_PATH}/icons/down-arrow.png);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView{\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    background-color: rgb(255, 255, 255);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView::item{\n"
                                                "    min-height: 20px;\n"
                                                "}")
            else:
                self.comboBox_bct.setStyleSheet("QComboBox{\n"
                                                "    background-color: rgb(255, 255, 255);\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    padding-top: 3px;\n"
                                                "    padding-bottom: 3px;\n"
                                                "    padding-left: 0px;\n"
                                                "    padding-right: 0px;\n"
                                                "}\n"
                                                "\n"
                                                "QComboBox::down-arrow{\n"
                                                rf"    image: url({REAL_PATH}/icons/down-arrow.png);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView{\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    background-color: rgb(255, 255, 255);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView::item{\n"
                                                "    min-height: 20px;\n"
                                                "}")

        return

    #----------------------------------------------#

    # function to remove the hover cursor when the checkbox is unchecked
    def clearDatapointsFromHover(self):

        # remove hover when unchecked
        if not self.checkBox_hover.isChecked():
            if self.mouseHoverFirstTime:
                self.plot_rawbuf0.removeItem(self.targetItem)
                self.mouseHoverFirstTime = False

    #----------------------------------------------#

    # function for the microsecond locker
    def lockMicroseconds(self):

        if self.pushButton_microseconds_lock.isChecked():
            self.pushButton_turns_lock.setChecked(False)
            self.pushButton_bunchs_lock.setChecked(True)
            self.pushButton_bunchs_lock.setText("1")
            self.pushButton_bunchs_lock.setStyleSheet("QPushButton{\n"
                                                     "    background-color: rgb(255, 255, 100);\n"
                                                     "    border: 2px solid #A6A6A6;\n"
                                                     "    padding-top: 4px;\n"
                                                     "    padding-bottom: 4px;\n"
                                                     "    padding-left: 6px;\n"
                                                     "    padding-right: 6px;\n"
                                                    "}")
        else:
            self.pushButton_bunchs_lock.setChecked(False)
            self.pushButton_bunchs_lock.setText("-")
            self.pushButton_bunchs_lock.setStyleSheet("QPushButton{\n"
                                                     "    background-color: rgb(255, 255, 255);\n"
                                                     "    border: 2px solid #A6A6A6;\n"
                                                     "    padding-top: 4px;\n"
                                                     "    padding-bottom: 4px;\n"
                                                     "    padding-left: 6px;\n"
                                                     "    padding-right: 6px;\n"
                                                    "}")

        return

    #----------------------------------------------#

    # function for the turn locker
    def lockTurns(self):

        if self.pushButton_turns_lock.isChecked():
            self.pushButton_microseconds_lock.setChecked(False)
            self.pushButton_bunchs_lock.setChecked(True)
            self.pushButton_bunchs_lock.setText("2")
            self.pushButton_bunchs_lock.setStyleSheet("QPushButton{\n"
                                                     "    background-color: rgb(255, 255, 100);\n"
                                                     "    border: 2px solid #A6A6A6;\n"
                                                     "    padding-top: 4px;\n"
                                                     "    padding-bottom: 4px;\n"
                                                     "    padding-left: 6px;\n"
                                                     "    padding-right: 6px;\n"
                                                    "}")
        else:
            self.pushButton_bunchs_lock.setChecked(False)
            self.pushButton_bunchs_lock.setText("-")
            self.pushButton_bunchs_lock.setStyleSheet("QPushButton{\n"
                                                     "    background-color: rgb(255, 255, 255);\n"
                                                     "    border: 2px solid #A6A6A6;\n"
                                                     "    padding-top: 4px;\n"
                                                     "    padding-bottom: 4px;\n"
                                                     "    padding-left: 6px;\n"
                                                     "    padding-right: 6px;\n"
                                                    "}")

        return

    #----------------------------------------------#

    # function to format the BCT pattern
    def formatBCTPattern(self, received_pattern = None):

        # set seed for random sequences
        if self.bct_use_random:
            np.random.seed(self.bct_random_seed)

        # init pattern for the whole sequence of data
        x_filling_pattern_full = deepcopy(self.time_vector)
        y_filling_pattern_full = [0] * len(self.time_vector)
        y_filling_pattern_full = np.array(y_filling_pattern_full)

        # generate random filling sequence
        if self.bct_use_random:
            y_filling_pattern = np.random.choice(2, 3564)
            y_filling_pattern = np.array(y_filling_pattern)
            y_filling_pattern = np.append(y_filling_pattern, 0)
            self.y_filling_pattern_not_empty = True
            print("{} - Using random pattern!".format(UI_FILENAME))
        elif self.bct_use_custom:
            y_filling_pattern = np.zeros(3564)
            y_filling_pattern[5:45] = 1
            y_filling_pattern = np.array(y_filling_pattern)
            y_filling_pattern = np.append(y_filling_pattern, 0)
            self.y_filling_pattern_not_empty = True
            print("{} - Using custom pattern!".format(UI_FILENAME))
        elif self.bct_from_sps:
            y_filling_pattern = np.zeros(3564)
            y_filling_pattern = np.array(y_filling_pattern)
            self.y_filling_pattern_not_empty = False
            print("{} - Empty BCT array from SPS!".format(UI_FILENAME))
        elif self.bct_use_received_pattern:
            y_filling_pattern = np.array(received_pattern)
            y_filling_pattern = np.append(y_filling_pattern, 0)
            if y_filling_pattern.any():
                self.y_filling_pattern_not_empty = True
                print("{} - Using BCT pattern from device!".format(UI_FILENAME))
            else:
                self.y_filling_pattern_not_empty = False
                print("{} - All elements of the received BCT pattern are zero!".format(UI_FILENAME))
        else:
            self.y_filling_pattern_not_empty = False
            print("{} - Pattern is empty or not found!".format(UI_FILENAME))

        # if it is empty, do not plot the pattern
        if self.y_filling_pattern_not_empty:

            # iterate over turns to loop the pattern
            for idx_turn in range(0, len(self.idx_flags_five_six)-1):

                # get lower and upper turn limits
                first_turn_ms = self.time_vector[self.idx_flags_five_six[idx_turn]]
                second_turn_ms = self.time_vector[self.idx_flags_five_six[idx_turn + 1]]
                n_samples = self.idx_flags_five_six[idx_turn + 1] - self.idx_flags_five_six[idx_turn]

                # the x filling pattern
                x_filling_pattern = np.linspace(first_turn_ms, second_turn_ms, num=3565)

                # interpolate
                interpolation_function = interp1d(x_filling_pattern, y_filling_pattern, kind='previous')
                x_filling_pattern_interpolated = np.linspace(first_turn_ms, second_turn_ms, num=n_samples)
                y_filling_pattern_interpolated = interpolation_function(x_filling_pattern_interpolated)

                # fill the full sequence
                y_filling_pattern_full[self.idx_flags_five_six[idx_turn]:self.idx_flags_five_six[idx_turn + 1]] = y_filling_pattern_interpolated

            # scale the full sequence
            y_filling_pattern_full = ((self.data_turn_line_eq_params_0[3] - self.data_turn_line_eq_params_0[2]) /
                                self.data_turn_line_eq_params_0[1]) * y_filling_pattern_full + self.data_turn_line_eq_params_0[2]

            # fix 1-sample error in the interpolation curve

            # case 1: perfect overlapping (no error) at the start of the slope
            # case 2: perfect overlapping (no error) at the end of the slope
            # case 3: slope starts too early
            # case 4: slope ends too late
            # case 5: slope starts too late (+1)
            # case 6: slope ends too early (-1)
            # case 7: slope starts too late (+2)
            # case 8: slope ends too early (-2)
            # case 9: slope starts too late (+3)
            # case 10: slope ends too early (-3)

            # iterate over bunches
            for idx_bunch in self.idx_flags_one_two:

                # skip over limits
                if idx_bunch - 3 < 0:
                    continue
                elif idx_bunch + 3 >= len(self.flags_bunch0):
                    continue

                # cases 1,2,3 and 4
                if y_filling_pattern_full[idx_bunch] == self.flags_bunch0[idx_bunch]:

                    # cases 1 and 2 (no error)
                    pass

                    # possible case 3
                    if y_filling_pattern_full[idx_bunch-1] == self.flags_bunch0[idx_bunch]:

                        # case 3
                        if y_filling_pattern_full[idx_bunch - 2] != self.flags_bunch0[idx_bunch]:
                            y_filling_pattern_full[idx_bunch - 1] = y_filling_pattern_full[idx_bunch - 2]
                            continue
                        elif y_filling_pattern_full[idx_bunch - 3] != self.flags_bunch0[idx_bunch]:
                            y_filling_pattern_full[idx_bunch - 2] = y_filling_pattern_full[idx_bunch - 3]
                            y_filling_pattern_full[idx_bunch - 1] = y_filling_pattern_full[idx_bunch - 2]
                            continue

                    # possible case 4
                    if y_filling_pattern_full[idx_bunch + 1] == self.flags_bunch0[idx_bunch]:

                        # case 4
                        if y_filling_pattern_full[idx_bunch + 2] != self.flags_bunch0[idx_bunch]:
                            y_filling_pattern_full[idx_bunch + 1] = y_filling_pattern_full[idx_bunch + 2]
                            continue
                        elif y_filling_pattern_full[idx_bunch + 3] != self.flags_bunch0[idx_bunch]:
                            y_filling_pattern_full[idx_bunch + 2] = y_filling_pattern_full[idx_bunch + 3]
                            y_filling_pattern_full[idx_bunch + 1] = y_filling_pattern_full[idx_bunch + 2]
                            continue

                #  case 5
                elif y_filling_pattern_full[idx_bunch + 1] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]

                # case 6
                elif y_filling_pattern_full[idx_bunch - 1] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]

                # case 7
                elif y_filling_pattern_full[idx_bunch + 2] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch + 1] = self.flags_bunch0[idx_bunch]

                # case 8
                elif y_filling_pattern_full[idx_bunch - 2] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch - 1] = self.flags_bunch0[idx_bunch]

                # case 9
                elif y_filling_pattern_full[idx_bunch + 3] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch + 1] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch + 2] = self.flags_bunch0[idx_bunch]

                # case 10
                elif y_filling_pattern_full[idx_bunch - 3] == self.flags_bunch0[idx_bunch]:
                    y_filling_pattern_full[idx_bunch] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch - 1] = self.flags_bunch0[idx_bunch]
                    y_filling_pattern_full[idx_bunch - 2] = self.flags_bunch0[idx_bunch]

            # save variables
            self.x_filling_pattern_full = x_filling_pattern_full
            self.y_filling_pattern_full = y_filling_pattern_full

        return

    #----------------------------------------------#

    # function to update the BCT pattern according to the introduced name
    def pushButtonApplyBCT(self, type):

        # get name
        if type == "lineedit":
            dev_name = self.lineEdit_bct_device_name.text()
            dev_name = dev_name.strip()
        elif type == "combobox":
            dev_name = str(self.comboBox_bct.currentText())
            dev_name = dev_name.strip()

        # check it is not empty
        if dev_name:

            # use predefined random format to debug the app
            # e.g. RANDOM.SEED.0 means use random pattern with seed 0
            # e.g. RANDOM.SEED.567 means use random pattern with seed 567
            if "RANDOM.SEED." in dev_name or "RANDOM.SEQUENCE." in dev_name:

                # update boolean
                self.bct_use_random = True
                self.bct_use_custom = False
                self.bct_use_received_pattern = False
                self.bct_from_sps = False

                # get seed
                rs = dev_name.split(".")[-1]

                # if it is not a number, the format is wrong so return
                if rs.isdecimal():
                    self.bct_random_seed = int(rs)
                else:
                    print("{} - Please introduce a correct RANDOM.SEED.X or RANDOM.SEQUENCE.X string!".format(UI_FILENAME))
                    return

                # format the pattern
                if self.bufferFirstPlotsPainted:
                    self.formatBCTPattern()
                    if self.bct_checked:
                        self.updateBCTPlot(state = self.checkBox_bct.checkState())

            # use other type of custom array
            elif "CUSTOM.SEQUENCE.0" in dev_name:

                # update boolean
                self.bct_use_random = False
                self.bct_use_custom = True
                self.bct_use_received_pattern = False
                self.bct_from_sps = False

                # format the pattern
                if self.bufferFirstPlotsPainted:
                    self.formatBCTPattern()
                    if self.bct_checked:
                        self.updateBCTPlot(state=self.checkBox_bct.checkState())

            # otherwise, get the pattern from the bct device
            # example names: LHC.BCTFR.A6R4.B1, LHC.BCTFR.A6R4.B2
            else:

                # trying to access to LHC.BCTFR.A6R4.B1 will give RBAC error since the device is inside LHC
                if self.current_accelerator == "SPS":

                    # update boolean
                    self.bct_use_random = False
                    self.bct_use_custom = False
                    self.bct_use_received_pattern = False
                    self.bct_from_sps = True

                    # format the pattern
                    if self.bufferFirstPlotsPainted:
                        self.formatBCTPattern()
                        if self.bct_checked:
                            self.updateBCTPlot(state=self.checkBox_bct.checkState())

                # normal procedure for LHC
                else:

                    # update boolean
                    self.bct_use_random = False
                    self.bct_use_custom = False
                    self.bct_use_received_pattern = True
                    self.bct_from_sps = False

                    # remove old bct
                    if self.counter_of_bct_apply >= 1:
                        self.data_bct_save = np.array([0])
                        self.CValueAggregator_BCT.updateTriggered['PyQt_PyObject'].disconnect(self.receiveDataFromBCTDevice)
                        self.horizontalLayout_CValueAggregators.removeWidget(self.CValueAggregator_BCT)
                        self.CValueAggregator_BCT.deleteLater()
                        self.CValueAggregator_BCT = None

                    # update counter
                    self.counter_of_bct_apply += 1

                    # aggregator for BCT
                    self.CValueAggregator_BCT = CValueAggregator(self)
                    self.CValueAggregator_BCT.setProperty("inputChannels", ['{}/Acquisition#bunchFillingPattern'.format(dev_name)])
                    self.CValueAggregator_BCT.setObjectName("CValueAggregator_BCT")
                    self.CValueAggregator_BCT.setValueTransformation("try:\n"
                                                                         "    output(next(iter(values.values())))\n"
                                                                         "except:\n"
                                                                         "    output(0)")
                    self.horizontalLayout_CValueAggregators.addWidget(self.CValueAggregator_BCT)

                    # BCT aggregator signals
                    self.CValueAggregator_BCT.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromBCTDevice)

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

                # cap the limits
                if lower_limit > self.time_vector[-1]:
                    lower_limit = self.time_vector[-1]
                if upper_limit > self.time_vector[-1]:
                    upper_limit = self.time_vector[-1]

                # sanity check
                if lower_limit >= upper_limit:

                    # error message
                    message_title = "WARNING"
                    message_text = "Please make sure that the upper limit is strictly bigger than the lower limit!"
                    self.message_box = QMessageBox.warning(self, message_title, message_text)
                    return

                # set range
                self.plot_rawbuf0.setXRange(lower_limit, upper_limit, padding=0)

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

                # sanity check
                if lower_limit >= upper_limit:

                    # error message
                    message_title = "WARNING"
                    message_text = "Please make sure that the upper limit is strictly bigger than the lower limit!"
                    self.message_box = QMessageBox.warning(self, message_title, message_text)
                    return

                # get the real bunch limits
                # if lower_limit == 0:
                #     bunchs_lower_limit = 0
                # elif lower_limit >= 1 and lower_limit <= len(self.idx_flags_one_two):
                #     bunchs_lower_limit = self.time_vector[self.idx_flags_one_two[lower_limit - 1]]
                # elif lower_limit > len(self.idx_flags_one_two):
                #     bunchs_lower_limit = self.time_vector[-1]
                # if upper_limit == 0:
                #     bunchs_upper_limit = 0
                # elif upper_limit >= 1 and upper_limit <= len(self.idx_flags_one_two):
                #     bunchs_upper_limit = self.time_vector[self.idx_flags_one_two[upper_limit - 1]]
                # elif upper_limit > len(self.idx_flags_one_two):
                #     bunchs_upper_limit = self.time_vector[-1]

                # lock mode: nothing
                if self.pushButton_bunchs_lock.text() == "-":

                    # get the real bunch limits
                    if lower_limit >= 0 and lower_limit <= len(self.idx_flags_one_two) - 1:
                        bunchs_lower_limit = self.time_vector[self.idx_flags_one_two[lower_limit]]
                    elif lower_limit >= len(self.idx_flags_one_two):
                        bunchs_lower_limit = self.time_vector[-1]
                    if upper_limit >= 0 and upper_limit <= len(self.idx_flags_one_two) - 1:
                        bunchs_upper_limit = self.time_vector[self.idx_flags_one_two[upper_limit]]
                    elif upper_limit >= len(self.idx_flags_one_two):
                        bunchs_upper_limit = self.time_vector[-1]

                # lock mode: microseconds and bunches
                elif self.pushButton_bunchs_lock.text() == "1":

                    # check line edits are not empty
                    if self.lineEdit_from_microseconds.text() and self.lineEdit_to_microseconds.text():

                        # get lower and upper limit
                        lower_limit_bunchs = lower_limit
                        upper_limit_bunchs = upper_limit
                        lower_limit_microseconds = self.lineEdit_from_microseconds.text()
                        upper_limit_microseconds = self.lineEdit_to_microseconds.text()
                        lower_limit_microseconds = float(lower_limit_microseconds.replace(",", "."))
                        upper_limit_microseconds = float(upper_limit_microseconds.replace(",", "."))

                        # get time
                        time_1 = lower_limit_microseconds
                        time_2 = upper_limit_microseconds

                        # get idx time
                        _, idx_time_1 = numpy_find_nearest(self.time_vector, time_1, side="left")
                        _, idx_time_2 = numpy_find_nearest(self.time_vector, time_2, side="left")

                        # reverse engineering idx flags
                        val_flag_1, idx_flag_1 = numpy_find_nearest(self.idx_flags_one_two, idx_time_1, side="left")
                        val_flag_2, idx_flag_2 = numpy_find_nearest(self.idx_flags_one_two, idx_time_2, side="right")

                        # calculate and cap values
                        if lower_limit_bunchs >= 0 and lower_limit_bunchs <= np.abs(idx_flag_2 - idx_flag_1):
                            bunchs_lower_limit = self.time_vector[self.idx_flags_one_two[lower_limit_bunchs+idx_flag_1]]
                        else:
                            bunchs_lower_limit = self.time_vector[val_flag_2]
                        if upper_limit_bunchs >= 0 and upper_limit_bunchs <= np.abs(idx_flag_2 - idx_flag_1):
                            bunchs_upper_limit = self.time_vector[self.idx_flags_one_two[upper_limit_bunchs+idx_flag_1]]
                        else:
                            bunchs_upper_limit = self.time_vector[val_flag_2]

                    # sanity check
                    else:

                        # error message
                        message_title = "WARNING"
                        message_text = "Please, specify a valid turn range first. If you desire to introduce only bunches, just disable the lock button (the yellow button at the right)."
                        self.message_box = QMessageBox.warning(self, message_title, message_text)
                        return

                # lock mode: turns and bunches
                elif self.pushButton_bunchs_lock.text() == "2":

                    # check line edits are not empty
                    if self.lineEdit_from_turns.text() and self.lineEdit_to_turns.text():

                        # get lower and upper limit
                        lower_limit_bunchs = lower_limit
                        upper_limit_bunchs = upper_limit
                        lower_limit_turns = self.lineEdit_from_turns.text()
                        upper_limit_turns = self.lineEdit_to_turns.text()
                        lower_limit_turns = int(lower_limit_turns.replace(",", "."))
                        upper_limit_turns = int(upper_limit_turns.replace(",", "."))

                        # cap turns
                        if lower_limit_turns >= len(self.inf_lines_pos_0):
                            lower_limit_turns = len(self.inf_lines_pos_0)-1
                        if upper_limit_turns >= len(self.inf_lines_pos_0):
                            upper_limit_turns = len(self.inf_lines_pos_0)-1

                        # get time
                        time_1 = self.inf_lines_pos_0[lower_limit_turns]
                        time_2 = self.inf_lines_pos_0[upper_limit_turns]

                        # get idx time
                        idx_time_1 = np.where(self.time_vector == time_1)[0]
                        idx_time_2 = np.where(self.time_vector == time_2)[0]

                        # reverse engineering idx flags
                        val_flag_1, idx_flag_1 = numpy_find_nearest(self.idx_flags_one_two, idx_time_1, side="left")
                        val_flag_2, idx_flag_2 = numpy_find_nearest(self.idx_flags_one_two, idx_time_2, side="right")

                        # calculate and cap values
                        if lower_limit_bunchs == 0:
                            bunchs_lower_limit = self.inf_lines_pos_0[lower_limit_turns]
                        elif lower_limit_bunchs >= 1 and lower_limit_bunchs < np.abs(idx_flag_2 - idx_flag_1):
                            bunchs_lower_limit = self.time_vector[self.idx_flags_one_two[lower_limit_bunchs+idx_flag_1-1]]
                        else:
                            bunchs_lower_limit = self.inf_lines_pos_0[upper_limit_turns]
                        if upper_limit_bunchs == 0:
                            bunchs_upper_limit = self.inf_lines_pos_0[lower_limit_turns]
                        elif upper_limit_bunchs >= 1 and upper_limit_bunchs < np.abs(idx_flag_2 - idx_flag_1):
                            bunchs_upper_limit = self.time_vector[self.idx_flags_one_two[upper_limit_bunchs+idx_flag_1-1]]
                        else:
                            bunchs_upper_limit = self.inf_lines_pos_0[upper_limit_turns]

                    # sanity check
                    else:

                        # error message
                        message_title = "WARNING"
                        message_text = "Please, specify a valid turn range first. If you desire to introduce only bunches, just disable the lock button (the yellow button at the right)."
                        self.message_box = QMessageBox.warning(self, message_title, message_text)
                        return

                # some debugging prints
                # print(time_1, time_2)
                # print(idx_time_1, idx_time_2)
                # print(val_flag_1, idx_flag_1, self.time_vector[val_flag_1])
                # print(val_flag_2, idx_flag_2, self.time_vector[val_flag_2])
                # print(bunchs_lower_limit)
                # print(bunchs_upper_limit)

                # set range
                self.plot_rawbuf0.setXRange(bunchs_lower_limit, bunchs_upper_limit, padding=0)

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

                # sanity check
                if lower_limit >= upper_limit:

                    # error message
                    message_title = "WARNING"
                    message_text = "Please make sure that the upper limit is strictly bigger than the lower limit!"
                    self.message_box = QMessageBox.warning(self, message_title, message_text)
                    return

                # get the real turn limits
                # if lower_limit == 0:
                #     turns_lower_limit = 0
                # elif lower_limit >= 1 and lower_limit <= len(self.inf_lines_pos_0):
                #     turns_lower_limit = self.inf_lines_pos_0[lower_limit - 1]
                # elif lower_limit > len(self.inf_lines_pos_0):
                #     turns_lower_limit = self.time_vector[-1]
                # if upper_limit == 0:
                #     turns_upper_limit = 0
                # elif upper_limit >= 1 and upper_limit <= len(self.inf_lines_pos_0):
                #     turns_upper_limit = self.inf_lines_pos_0[upper_limit - 1]
                # elif upper_limit > len(self.inf_lines_pos_0):
                #     turns_upper_limit = self.time_vector[-1]

                # get the real turn limits
                if lower_limit >= 0 and lower_limit <= len(self.inf_lines_pos_0) - 1:
                    turns_lower_limit = self.inf_lines_pos_0[lower_limit]
                elif lower_limit >= len(self.inf_lines_pos_0):
                    turns_lower_limit = self.time_vector[-1]
                if upper_limit >= 0 and upper_limit <= len(self.inf_lines_pos_0) - 1:
                    turns_upper_limit = self.inf_lines_pos_0[upper_limit]
                elif upper_limit >= len(self.inf_lines_pos_0):
                    turns_upper_limit = self.time_vector[-1]

                # set range
                self.plot_rawbuf0.setXRange(turns_lower_limit, turns_upper_limit, padding=0)

        return

    #----------------------------------------------#

    # function to handle command clicks
    def commandClicked(self):

        # status bar message
        self.app.main_window.statusBar().showMessage("Command clicked!", 3*1000)
        self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that performs the autophasing
    def phaseAutoTuning(self):

        # status bar message
        self.app.main_window.statusBar().showMessage("Command clicked!", 3*1000)
        self.app.main_window.statusBar().repaint()

        # do not repeat autophasing for the same data
        if np.array_equal(self.old_data_for_autophasing, self.data_rawBuf0):
            message_title = "WARNING"
            message_text = "You have already auto-tuned the parameters. Wait until the reception of new data in order to run this command again. " \
                           "You can try running the TriggerCapture command to check the results (even though it should have already been run after the previous PhaseAutoTuning iteration)."
            self.reply = QMessageBox.warning(self, message_title, message_text)
            return

        self.box_bct_or_slot = QMessageBox()
        self.box_bct_or_slot.setIcon(QMessageBox.Question)
        self.box_bct_or_slot.setWindowTitle('PhaseAutoTuning Wizard')
        self.box_bct_or_slot.setText("You are about to run the PhaseAutoTuning command. This command will automatically change and set the ExpertSetting parameters. Remember that it is usually a good idea to manually set the delay params to 0 and perform a trigger before running this command. There are two available modes:\n\n"
                    "1. BCT mode. Adjust the loss signal with respect to the BCT received signal. Make sure a valid BCT source is selected and applied beforehand.\n\n"
                    "2. Bunch slot mode. Adjust the loss signal so that it aligns with respect to the bunch slot selected by the user.\n")
        self.box_bct_or_slot.addButton("BCT mode", QMessageBox.NoRole)
        self.box_bct_or_slot.addButton("Bunch slot mode", QMessageBox.YesRole)
        self.box_bct_or_slot.addButton("Cancel", QMessageBox.RejectRole)
        self.box_bct_or_slot.setWindowIcon(QIcon(os.path.join(REAL_PATH, "icons/diamond_2.png")))
        self.reply = self.box_bct_or_slot.exec_()

        # CANCEL
        if self.reply == 2:

            # just quit the wizard
            return

        # BCT MODE
        elif self.reply == 0:

            # first check if bct exists, otherwise stop running the command
            if not self.y_filling_pattern_not_empty:
                message_title = "WARNING"
                message_text = "BCT signal is empty or not being found. Please, select a valid BCT device and press the \"Apply\" button on the panel above."
                self.reply = QMessageBox.warning(self, message_title, message_text)
                return

            # 0. do a GET beforehand
            self.getFunction()

            # 1. crop the signal and the BCT around the first turn to get a short and good interval

            # get idx time of first turn
            idx_time = int(np.where(self.time_vector == self.inf_lines_pos_0[0])[0])

            # get amount of samples between turns
            n_samples_between_turns = int(np.where(self.time_vector == self.inf_lines_pos_0[1])[0] - idx_time)

            # crop the signals
            decim = 3
            x_bct_cropped = self.x_filling_pattern_full[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]
            y_bct_cropped = self.y_filling_pattern_full[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]
            x_signal_cropped = self.time_vector[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]
            y_signal_cropped = self.data_rawBuf0[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]

            # 2. get BCT first 1-bunch peak index
            first_bct_peak_index = y_bct_cropped.argmax()

            # 3. get loss signal first peak

            # hyperparams
            lag = 1000
            threshold = 20
            influence = 0.2

            # run algorithm
            result = thresholding_algo(y_signal_cropped, lag=lag, threshold=threshold, influence=influence)

            # get first peak
            first_signal_peak_index = result["signals"].argmax()

            # debug plot
            # import pylab
            # y = y_signal_cropped
            # pylab.subplot(211)
            # pylab.plot(np.arange(1, len(y) + 1), y)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"], color="cyan", lw=2)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"] + threshold * result["stdFilter"], color="green", lw=2)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"] - threshold * result["stdFilter"], color="green", lw=2)
            # pylab.subplot(212)
            # pylab.step(np.arange(1, len(y) + 1), result["signals"], color="red", lw=2)
            # pylab.ylim(-1.5, 1.5)
            # pylab.show()
            # print(first_bct_peak_index, first_signal_peak_index, x_signal_cropped[first_bct_peak_index], x_signal_cropped[first_signal_peak_index])

            # 4. calculate the difference to set the params (distance between samples is 1.53ns or 650MHz)
            difference_in_samples = first_signal_peak_index - first_bct_peak_index
            difference_in_nanoseconds = (1000/650) * difference_in_samples

            # if the difference is positive, the loss signal is to the right of the BCT
            if difference_in_nanoseconds > 0:

                # 5. calculate the tuning of the parameters (delay = coarse*n_coarse + thin*n_thin)
                coarse_delay = int(round(difference_in_nanoseconds / 25) + 2)
                thin_delay = int(round(((coarse_delay * 25) - difference_in_nanoseconds) / (1000/650)))

                # use this to get the peak in the middle of the bunch slot
                thin_delay += int(round((25 / (1000/650)) / 3))

            # if the difference is negative, the loss signal is to the left of the BCT
            else:

                # 5. calculate the tuning of the parameters (delay = coarse*n_coarse + thin*n_thin)
                coarse_delay = 0
                thin_delay = int(round(-1*difference_in_nanoseconds / (1000 / 650)))

                # use this to get the peak in the middle of the bunch slot
                thin_delay += int(round((25 / (1000 / 650)) / 3))

            # do the settings
            self.delaySet(difference_in_nanoseconds, coarse_delay, thin_delay)

        # BUNCH SLOT MODE
        elif self.reply == 1:

            self.dialog_lineedit = DialogWithLineEdit()
            self.dialog_lineedit.setModal(True)
            self.dialog_lineedit.accepted_boolean.connect(self.closeDialogWithLineEdit)
            self.dialog_lineedit.show()

            return

        return

    #----------------------------------------------#

    # function that sets the estimated delay
    def delaySet(self, difference_in_nanoseconds, coarse_delay, thin_delay):

        # just a print
        print("{} - Estimated phasing difference: {}ns".format(UI_FILENAME, difference_in_nanoseconds))
        print("{} - Factors: {} (Coarse) and {} (Thin)".format(UI_FILENAME, coarse_delay, thin_delay))

        # 6. update table and press SET

        # show result message to inform the user
        message_title = "PhaseAutoTuning Wizard"
        message_text = "The estimated delay between signals is {:.2f}ns. Do you want to perform the following changes in the parameters?\n\n" \
                       "FBDEPTH (Thin delay) = {} ---> {}\nSYNCDELDEPTH (Coarse delay) = {} ---> {}".format(difference_in_nanoseconds,
                         int(self.data_model_expert_setting[0][-2]), int(self.data_model_expert_setting[0][-2]) + thin_delay,
                         int(self.data_model_expert_setting[1][-2]), int(self.data_model_expert_setting[1][-2]) + coarse_delay)
        self.reply = QMessageBox.question(self, message_title, message_text)

        # if user clicked yes, do the setting
        if self.reply == QMessageBox.Yes:

            # init data list
            new_data_model_expert_setting = []

            # iterate over table
            for row_counter, row_values in enumerate(self.data_model_expert_setting):

                # retrieve values
                field = self.list_of_delay_params[row_counter]
                old_value = row_values[-2]
                new_value = row_values[-1]

                # adjust the thin delay
                if row_counter == 0:
                    new_value = str(int(old_value) + thin_delay)

                # adjust the thin delay
                elif row_counter == 1:
                    new_value = str(int(old_value) + coarse_delay)

                # do not update skew
                else:
                    pass

                # append the estimated new values
                new_data_model_expert_setting.append([str(self.list_of_delay_params_user_friendly[row_counter]), self.step_list[row_counter], str(old_value), str(new_value)])

            # update data model
            self.data_model_expert_setting = new_data_model_expert_setting

            # update model
            self.data_table_model_expert_setting = TableModel(data=self.data_model_expert_setting, header_labels=["BST", "Steps", "Old Value", "New Value"], three_column_window=True, tooltip_list=self.tooltip_list)
            self.table_expert_setting.setModel(self.data_table_model_expert_setting)
            self.table_expert_setting.update()

            # update groupbox size in function of the number of rows
            self.groupbox_expert_setting.setFixedHeight(int(36 * (len(self.data_model_expert_setting) + 2)))

            # apply set
            self.setFunction()

            # save data rawbuf so that auto phasing is not repeated with the same data
            self.old_data_for_autophasing = deepcopy(self.data_rawBuf0)

            # ask for trigger
            message_title = "PhaseAutoTuning Wizard"
            message_text = "Do you also want to perform a TriggerCapture to check the results?"
            self.reply = QMessageBox.question(self, message_title, message_text)

            # if user clicked yes, run the TriggerCapture
            if self.reply == QMessageBox.Yes:

                # click trigger
                self.ccommandbutton_1.click()

        return

    #----------------------------------------------#

    # function that continues the autotuning wizard when the bunch slot is selected
    def closeDialogWithLineEdit(self, accepted):

        # retrieve bunch number
        bunch_number = int(self.dialog_lineedit.lineEdit.text())

        # close the dialog
        self.dialog_lineedit.close()

        # proceed to calculate the delay if the user accepted
        if accepted:

            # 0. do a GET beforehand
            self.getFunction()

            # 1. crop the signal and the BCT around the first turn to get a short and good interval

            # get idx time of first turn
            idx_time = int(np.where(self.time_vector == self.inf_lines_pos_0[0])[0])

            # get amount of samples between turns
            n_samples_between_turns = int(np.where(self.time_vector == self.inf_lines_pos_0[1])[0] - idx_time)

            # crop the signals
            decim = 3
            x_signal_cropped = self.time_vector[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]
            y_signal_cropped = self.data_rawBuf0[idx_time-int(n_samples_between_turns/decim):idx_time+int(n_samples_between_turns/decim)]

            # 2. get BCT first 1-bunch peak index

            time_1 = self.inf_lines_pos_0[0]
            time_2 = self.inf_lines_pos_0[1]
            idx_time_1 = np.where(self.time_vector == time_1)[0]
            idx_time_2 = np.where(self.time_vector == time_2)[0]
            val_flag_1, idx_flag_1 = numpy_find_nearest(self.idx_flags_one_two, idx_time_1, side="left")
            val_flag_2, idx_flag_2 = numpy_find_nearest(self.idx_flags_one_two, idx_time_2, side="right")
            if bunch_number == 0:
                first_bct_peak_index = idx_time_1[0]
            elif bunch_number >=1 and bunch_number < np.abs(idx_flag_2 - idx_flag_1) - 1:
                first_bct_peak_index = self.idx_flags_one_two[bunch_number + idx_flag_1 - 1][0]
            else:
                first_bct_peak_index = idx_time_2[0]

            # offset due to the cropping
            first_bct_peak_index -= (idx_time - int(n_samples_between_turns / decim))

            # 3. get loss signal first peak

            # hyperparams
            lag = 1000
            threshold = 20
            influence = 0.2

            # run algorithm
            result = thresholding_algo(y_signal_cropped, lag=lag, threshold=threshold, influence=influence)

            # get first peak
            first_signal_peak_index = result["signals"].argmax()

            # debug plot
            # import pylab
            # y = y_signal_cropped
            # pylab.subplot(211)
            # pylab.plot(np.arange(1, len(y) + 1), y)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"], color="cyan", lw=2)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"] + threshold * result["stdFilter"], color="green", lw=2)
            # pylab.plot(np.arange(1, len(y) + 1), result["avgFilter"] - threshold * result["stdFilter"], color="green", lw=2)
            # pylab.subplot(212)
            # pylab.step(np.arange(1, len(y) + 1), result["signals"], color="red", lw=2)
            # pylab.ylim(-1.5, 1.5)
            # pylab.show()
            # print(first_bct_peak_index, first_signal_peak_index, x_signal_cropped[first_bct_peak_index], x_signal_cropped[first_signal_peak_index])

            # 4. calculate the difference to set the params (distance between samples is 1.53ns or 650MHz)
            difference_in_samples = first_signal_peak_index - first_bct_peak_index
            difference_in_nanoseconds = (1000/650) * difference_in_samples

            # if the difference is positive, the loss signal is to the right of the BCT
            if difference_in_nanoseconds > 0:

                # 5. calculate the tuning of the parameters (delay = coarse*n_coarse + thin*n_thin)
                coarse_delay = int(round(difference_in_nanoseconds / 25) + 2)
                thin_delay = int(round(((coarse_delay * 25) - difference_in_nanoseconds) / (1000/650)))

                # use this to get the peak in the middle of the bunch slot
                thin_delay += int(round((25 / (1000 / 650)) / 3))

            # if the difference is negative, the loss signal is to the left of the BCT
            else:

                # 5. calculate the tuning of the parameters (delay = coarse*n_coarse + thin*n_thin)
                coarse_delay = 0
                thin_delay = int(round(-1*difference_in_nanoseconds / (1000 / 650)))

                # use this to get the peak in the middle of the bunch slot
                thin_delay += int(round((25 / (1000 / 650)) / 3))

            # do the settings
            self.delaySet(difference_in_nanoseconds, coarse_delay, thin_delay)

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

    # connect function
    def receiveDataFromBCTDevice(self, data, verbose = False):

        # check that the arrays are different with respect to the previous iteration
        if self.bufferFirstPlotsPainted:
            if np.array_equal(self.data_bct_save, data):
                return

        # save data to check if it is exactly the same
        self.data_bct_save = data

        # format the pattern
        if self.bufferFirstPlotsPainted:
            self.formatBCTPattern(received_pattern = data)
            if self.bct_checked:
                self.updateBCTPlot(state=self.checkBox_bct.checkState())

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

        # save bunch idx for the zooming options
        self.idx_flags_one_two = idx_flags_one_two

        # get only turn flags (5 and 6) for buf0
        idx_flags_five_six = np.where((self.data_rawBufFlags0 == 5) | (self.data_rawBufFlags0 == 6))[0]
        flags_five_six = np.zeros(self.data_rawBufFlags0.shape)
        flags_five_six[idx_flags_five_six] = 1
        self.inf_lines_pos_0 = self.time_vector[idx_flags_five_six]

        # save bunch idx for the bct
        self.idx_flags_five_six = idx_flags_five_six

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

        # get and format the pattern
        self.formatBCTPattern()

        # freeze condition
        if not self.freeze_everything:

            # plot the data for buf0
            self.plot_rawbuf0.getPlotItem().clear()
            if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
            if self.y_filling_pattern_not_empty and self.bct_checked:
                self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                self.plotted_bct_at_least_once = True
            self.curve = self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
            if self.flags_turn0.size != 0 and self.is_turn0_checked:
                # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                for line_pos in self.inf_lines_pos_0:
                    infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                    self.plot_rawbuf0.addItem(infinite_line)
            self.mouseHoverFirstTime = False
            self.curve.scene().sigMouseMoved.connect(self.onMouseMoved)
            self.plot_rawbuf0.show()

            # set cycle information
            self.CLabel_acqStamp_Capture.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
            self.CLabel_cycleName_Capture.setText("<b>cycleName:</b> {}".format(self.data_cycleName))

        # update first plot boolean
        self.bufferFirstPlotsPainted = True

        # enable buttons
        self.checkBox_bunch.setEnabled(True)
        self.checkBox_turn.setEnabled(True)
        self.checkBox_bct.setEnabled(True)
        self.checkBox_hover.setEnabled(True)
        self.checkBox_sync_main.setEnabled(True)
        self.groupbox_zooming.setEnabled(True)

        # set validators
        self.lineEdit_from_microseconds.setValidator(QDoubleValidator(0, self.time_vector[-1], 4, self, notation=QDoubleValidator.StandardNotation))
        self.lineEdit_to_microseconds.setValidator(QDoubleValidator(0, self.time_vector[-1], 4, self, notation=QDoubleValidator.StandardNotation))
        self.lineEdit_from_turns.setValidator(QIntValidator(0, len(self.inf_lines_pos_0)-1, self))
        self.lineEdit_to_turns.setValidator(QIntValidator(0, len(self.inf_lines_pos_0)-1, self))
        self.lineEdit_from_bunchs.setValidator(QIntValidator(0, len(self.idx_flags_one_two)-1, self))
        self.lineEdit_to_bunchs.setValidator(QIntValidator(0, len(self.idx_flags_one_two)-1, self))

        return

    #----------------------------------------------#

    # function that gets the hover event of pyqtgraph
    def onMouseMoved(self, point):

        # only if checkbox is enabled
        if self.checkBox_hover.isChecked():

            # set label opts
            label_opts = {'fill': '#000000', 'border': '#00FF00', 'color': '#00FF00', 'offset': QPoint(0, 20)}

            # get the cursor
            p = self.plot_rawbuf0.plotItem.vb.mapSceneToView(point)

            # get closest time value
            closest_val, closest_idx = numpy_find_nearest(self.time_vector, p.x(), side="left")

            # interpolated values
            x_val = closest_val
            y_val = self.data_rawBuf0[closest_idx]

            # format the point
            x_formatted = "%.3f" % x_val
            y_formatted = "%.3f" % y_val

            # first time check
            if not self.mouseHoverFirstTime:

                # add to the plot
                self.mouseHoverFirstTime = True
                self.targetItem = pg.TargetItem(movable=False, pos=(x_val, y_val), label="({}, {})".format(x_formatted, y_formatted), symbol="o", size=8, pen="#00FF00", labelOpts=label_opts)
                self.plot_rawbuf0.addItem(self.targetItem)

            # if it is not the first time
            else:

                # update the cursor
                self.targetItem.setPos((x_val, y_val))
                self.targetItem.setLabel("({}, {})".format(x_formatted, y_formatted), labelOpts=label_opts)

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

    # function for drawing the bct plot
    def updateBCTPlot(self, state):

        # reset clip to view to avoid errors
        if self.y_filling_pattern_not_empty or self.plotted_bct_at_least_once:
            self.plot_rawbuf0.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - BCT button checked...".format(UI_FILENAME))
            self.bct_checked = True
            if self.y_filling_pattern_not_empty or self.plotted_bct_at_least_once:
                if self.bufferFirstPlotsPainted:
                    self.plot_rawbuf0.getPlotItem().clear()
                    if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                        self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
                    if self.y_filling_pattern_not_empty and self.bct_checked:
                        self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                        self.plotted_bct_at_least_once = True
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                    if self.flags_turn0.size != 0 and self.is_turn0_checked:
                        # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                        for line_pos in self.inf_lines_pos_0:
                            infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                            self.plot_rawbuf0.addItem(infinite_line)
                    self.mouseHoverFirstTime = False
                    self.plot_rawbuf0.show()

        # if not
        else:

            # remove the flags
            print("{} - BCT button unchecked...".format(UI_FILENAME))
            self.bct_checked = False
            if self.y_filling_pattern_not_empty or self.plotted_bct_at_least_once:
                if self.bufferFirstPlotsPainted:
                    self.plot_rawbuf0.getPlotItem().clear()
                    if self.flags_bunch0.size != 0 and self.is_bunch0_checked:
                        self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_bunch0, pen=QColor("#EF476F"), name="rawBuf0_bunch_flags")
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                    if self.flags_turn0.size != 0 and self.is_turn0_checked:
                        # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                        for line_pos in self.inf_lines_pos_0:
                            infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                            self.plot_rawbuf0.addItem(infinite_line)
                    self.mouseHoverFirstTime = False
                    self.plot_rawbuf0.show()

        # reset clip to view to avoid errors
        if self.y_filling_pattern_not_empty or self.plotted_bct_at_least_once:
            self.plot_rawbuf0.getPlotItem().setClipToView(True)

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
                if self.y_filling_pattern_not_empty and self.bct_checked:
                    self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                    self.plotted_bct_at_least_once = True
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.mouseHoverFirstTime = False
                self.plot_rawbuf0.show()

        # if not
        else:

            # remove the flags
            print("{} - Bunchs0 button unchecked...".format(UI_FILENAME))
            self.current_flags_dict["1,2"] = False
            self.is_bunch0_checked = False
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                if self.y_filling_pattern_not_empty and self.bct_checked:
                    self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                    self.plotted_bct_at_least_once = True
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.mouseHoverFirstTime = False
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
                if self.y_filling_pattern_not_empty and self.bct_checked:
                    self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                    self.plotted_bct_at_least_once = True
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    # self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                    for line_pos in self.inf_lines_pos_0:
                        infinite_line = pg.InfiniteLine(pos=line_pos, movable=False, angle=90, pen={'color': (255, 255, 0), 'width': 1.5}, label=None)
                        self.plot_rawbuf0.addItem(infinite_line)
                self.mouseHoverFirstTime = False
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
                if self.y_filling_pattern_not_empty and self.bct_checked:
                    self.plot_rawbuf0.plot(x=self.x_filling_pattern_full, y=self.y_filling_pattern_full, pen=(0, 0, 255), name="filling_pattern_full")
                    self.plotted_bct_at_least_once = True
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.mouseHoverFirstTime = False
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
            self.app.main_window.setWindowIcon(QIcon(os.path.join(REAL_PATH, "icons/diamond_2.png")))

            # init GET
            self.getFunction(show_message=False)

            # hide the log console (not needed when using launcher.py)
            # self.app.main_window.hide_log_console()

            # try to know if it is B1 or B2 beam
            self.beam_string = ""
            try:
                monitor_names = self.japc.getParam("{}/{}#{}".format(self.current_device, "GeneralInformation", "monitorNames"), timingSelectorOverride="", getHeader=False, noPyConversion=False)
                last_string = monitor_names[0].split(".")[-1]
                if last_string == "B1":
                    self.beam_string = "B1"
                elif last_string == "B2":
                    self.beam_string = "B2"
            except:
                pass

            # set main combobox item based on the beam string
            if self.beam_string:

                # draw the dropdown
                selected_index = 0
                self.color_indexes_for_combobox = []
                self.comboBox_bct.clear()
                self.model_combobox = self.comboBox_bct.model()
                for row_idx, row in enumerate(self.items_combobox):
                    item_to_append = QStandardItem(str(row))
                    if row.find(self.beam_string) != -1:
                        item_to_append.setBackground(QColor('#ffff66'))
                        if selected_index == 0:
                            selected_index = row_idx
                        self.color_indexes_for_combobox.append(row_idx)
                    self.model_combobox.appendRow(item_to_append)
                self.comboBox_bct.setModel(self.model_combobox)

                # draw the combo
                self.comboBox_bct.setStyleSheet("QComboBox{\n"
                                                "    background-color: #ffff66;\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    padding-top: 3px;\n"
                                                "    padding-bottom: 3px;\n"
                                                "    padding-left: 0px;\n"
                                                "    padding-right: 0px;\n"
                                                "}\n"
                                                "\n"
                                                "QComboBox::down-arrow{\n"
                                                rf"    image: url({REAL_PATH}/icons/down-arrow.png);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView{\n"
                                                "    border: 2px solid #A6A6A6;\n"
                                                "    background-color: rgb(255, 255, 255);\n"
                                                "}\n"
                                                "QComboBox QAbstractItemView::item{\n"
                                                "    min-height: 20px;\n"
                                                "}")

                # select the first valid index
                self.comboBox_bct.setCurrentIndex(selected_index)

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