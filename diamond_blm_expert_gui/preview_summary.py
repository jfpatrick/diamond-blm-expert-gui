########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont)
from PyQt5.QtCore import (QSize, Qt, QRect)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import numpy as np
from general_utils import createCustomTempDir, getSystemTempDir

########################################################
########################################################

# GLOBALS

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
UI_FILENAME = "preview_summary.ui"

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

        # set the device list
        self.device_list = ["SP.BA1.BLMDIAMOND.2", "SP.BA2.BLMDIAMOND.2", "SP.BA4.BLMDIAMOND.2", "SP.BA6.BLMDIAMOND.2", "dBLM.TEST4"]
        self.LoadDeviceListFromTxtPremain()

        # order the device list
        self.device_list.sort()

        # input the property list
        self.field_list = ["BeamMomentum", "BstShift", "BunchSample", "FpgaCompilation", "FpgaFirmware", "FpgaStatus", "TurnBc", "TurnDropped", "TurnSample"]

        # order the property list
        self.field_list.sort()

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

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # initialize widget dicts
        self.layoutDict = {}
        self.labelDict = {}

        # create the main widget
        self.main_widget = QWidget(self.scrollingContents_properties)
        self.main_widget.setObjectName("main_widget")

        # widget layout
        self.layoutDict["grid_layout_main_widget"] = QGridLayout(self.main_widget)
        self.layoutDict["grid_layout_main_widget"].setObjectName("grid_layout_main_widget")

        # top spacer
        spacer_top = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_scrollingContents_properties.addItem(spacer_top)

        # add the top title labels (the first row of the table)
        row = 0

        # set device label (column == 0)
        column = 0
        self.labelDict["{}_{}".format("main_widget", "title_device")] = QLabel(self.main_widget)
        self.labelDict["{}_{}".format("main_widget", "title_device")].setObjectName("label_{}_{}".format("main_widget", "title_device"))
        self.labelDict["{}_{}".format("main_widget", "title_device")].setMinimumSize(QSize(160, 32))
        self.labelDict["{}_{}".format("main_widget", "title_device")].setAlignment(Qt.AlignCenter)
        self.labelDict["{}_{}".format("main_widget", "title_device")].setText("{}".format("Device"))
        self.labelDict["{}_{}".format("main_widget", "title_device")].setStyleSheet("background-color: rgb(210, 210, 210);")
        self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["{}_{}".format("main_widget", "title_device")], row, column, 1, 1)

        # continue iterating for the rest of field names
        column = 1
        for field in self.field_list:

            # set title label
            self.labelDict["{}_title_{}".format("main_widget", field)] = QLabel(self.main_widget)
            self.labelDict["{}_title_{}".format("main_widget", field)].setObjectName("label_{}_{}".format("main_widget", field))
            self.labelDict["{}_title_{}".format("main_widget", field)].setMinimumSize(QSize(160, 32))
            self.labelDict["{}_title_{}".format("main_widget", field)].setAlignment(Qt.AlignCenter)
            self.labelDict["{}_title_{}".format("main_widget", field)].setText("{}".format(field))
            self.labelDict["{}_title_{}".format("main_widget", field)].setStyleSheet("background-color: rgb(210, 210, 210);")
            self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["{}_title_{}".format("main_widget", field)], row, column, 1, 1)

            # go for the next column
            column += 1

        # iterate over all devices and fill all the fields
        row = 1
        maxMinWidth = 0
        for device in self.device_list:

            # if the device IS working
            if device in self.working_devices:

                # get the field values of the device via pyjapc
                field_values = self.japc.getParam("{}/{}".format(device, "GeneralInformation"))

                # set device name (column == 0)
                column = 0
                self.labelDict["{}_{}".format("main_widget", device)] = QLabel(self.main_widget)
                self.labelDict["{}_{}".format("main_widget", device)].setObjectName("label_{}_{}".format("main_widget", "title_device"))
                self.labelDict["{}_{}".format("main_widget", device)].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format("main_widget", device)].setText("{}".format(device))
                minWidth = self.labelDict["{}_{}".format("main_widget", device)].fontMetrics().boundingRect(self.labelDict["{}_{}".format("main_widget", device)].text()).width()
                if minWidth > maxMinWidth:
                    maxMinWidth = minWidth
                self.labelDict["{}_{}".format("main_widget", device)].setMinimumSize(QSize(np.abs(maxMinWidth+round(0.1*maxMinWidth)), 32))
                self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["{}_{}".format("main_widget", device)], row, column, 1, 1)

                # iterate over the rest of fields
                column = 1
                for field in self.field_list:

                    # if the field is monitorNames, process the string a little bit for the sake of aesthetics
                    if field == "monitorNames":
                        final_field_value = ""
                        new_val = list(dict.fromkeys(field_values[field]))
                        for i in range(0, len(new_val)):
                            string = new_val[i]
                            if i > 0:
                                final_field_value = final_field_value + ", " + string
                            else:
                                final_field_value = string
                        final_field_value = "  {}  ".format(final_field_value)

                    # just use the default field value
                    else:
                        final_field_value = field_values[field]

                    # set label
                    self.labelDict["label_value_{}_{}".format("main_widget", field)] = QLabel(self.main_widget)
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setObjectName("label_value_{}_{}".format("main_widget", field))
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setText("{}".format(final_field_value))
                    minWidth = self.labelDict["label_value_{}_{}".format("main_widget", field)].fontMetrics().boundingRect(self.labelDict["label_value_{}_{}".format("main_widget", field)].text()).width()
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setMinimumSize(QSize(np.abs(minWidth), 32))
                    self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["label_value_{}_{}".format("main_widget", field)], row, column, 1, 1)

                    # go for the next column (field)
                    column += 1

            # if the device IS NOT working
            else:

                # set device name (column == 0)
                column = 0
                self.labelDict["{}_{}".format("main_widget", device)] = QLabel(self.main_widget)
                self.labelDict["{}_{}".format("main_widget", device)].setObjectName("label_{}_{}".format("main_widget", "title_device"))
                self.labelDict["{}_{}".format("main_widget", device)].setMinimumSize(QSize(8*len(str(device)), 32))
                self.labelDict["{}_{}".format("main_widget", device)].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format("main_widget", device)].setTextFormat(Qt.RichText)
                self.labelDict["{}_{}".format("main_widget", device)].setText("<font color=red>{}</font>".format(device))
                self.labelDict["{}_{}".format("main_widget", device)].setStyleSheet("background-color: #ffebeb;")
                self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["{}_{}".format("main_widget", device)], row, column, 1, 1)

                # iterate over the rest of fields
                column = 1
                for field in self.field_list:

                    # the field value is just null because the device does not work
                    final_field_value = "Null"

                    # set label
                    self.labelDict["label_value_{}_{}".format("main_widget", field)] = QLabel(self.main_widget)
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setObjectName("label_value_{}_{}".format("main_widget", field))
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setTextFormat(Qt.RichText)
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setText("<font color=red>{}</font>".format(final_field_value))
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setStyleSheet("background-color: #ffebeb;")
                    minWidth = self.labelDict["label_value_{}_{}".format("main_widget", field)].fontMetrics().boundingRect(self.labelDict["label_value_{}_{}".format("main_widget", field)].text()).width()
                    self.labelDict["label_value_{}_{}".format("main_widget", field)].setMinimumSize(QSize(np.abs(minWidth), 32))
                    self.layoutDict["grid_layout_main_widget"].addWidget(self.labelDict["label_value_{}_{}".format("main_widget", field)], row, column, 1, 1)

                    # go for the next column (field)
                    column += 1

            # go for the next row (device)
            row += 1

        # add the widget to the scrolling layout
        self.verticalLayout_scrollingContents_properties.addWidget(self.main_widget)

        # bottom spacer
        spacer_bottom = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_scrollingContents_properties.addItem(spacer_bottom)

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2.5)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

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

########################################################
########################################################