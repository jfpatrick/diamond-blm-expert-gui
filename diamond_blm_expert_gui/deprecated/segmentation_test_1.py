########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont)
from PyQt5.QtCore import (QSize, Qt, QRect, QTimer)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import faulthandler

########################################################
########################################################

# GLOBALS

UI_FILENAME = "segmentation_test_1.ui"

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

        faulthandler.enable()

        # load the gui, build the widgets and handle the signals
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)



        self.japc = pyjapc.PyJapc()


        # new device binding
        self.pushButton.clicked.connect(self.openNewDevice)

        self.timer_open_device = QTimer(self)
        self.timer_open_device.setInterval(1000)
        self.timer_open_device.timeout.connect(self.click_button)
        # self.timer_open_device.start()


        return

    def click_button(self):
        self.pushButton.click()
        return


    # function that overwrites the txt file so that the premain.py can open the new device panel
    def openNewDevice(self):

        # print the OPEN DEVICE action
        print("{} - Button OPEN DEVICE pressed".format(UI_FILENAME))

        # open main container
        self.CEmbeddedDisplay.filename = ""
        self.CEmbeddedDisplay.hide()
        self.CEmbeddedDisplay.show()
        self.CEmbeddedDisplay.filename = "segmentation_test_2.py"
        self.CEmbeddedDisplay.open_file()

        return