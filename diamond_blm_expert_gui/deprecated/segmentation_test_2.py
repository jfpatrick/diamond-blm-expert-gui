########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

import faulthandler

from comrad import (CApplication, CLineEdit, CCommandButton, CLabel, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont)
from PyQt5.QtCore import (QSize, Qt, QRect)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc

# import threading

########################################################
########################################################

# GLOBALS

UI_FILENAME = "segmentation_test_2.ui"

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

        # print(threading.currentThread())

        # faulthandler.enable()

        # load the gui, build the widgets and handle the signals
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)

        # aggregator for Capture
        """
        self.japc = pyjapc.PyJapc()
        self.japc.setSelector("SPS.USER.ALL")
        self.japc.subscribeParam("SP.UA87.BLMDIAMOND.3/Capture", self.myCallback)
        self.japc.startSubscriptions()
        """

        self.CValueAggregator.setProperty("inputChannels", ['{}/Capture'.format("SP.UA87.BLMDIAMOND.3")])

        self.CValueAggregator.setObjectName("CValueAggregator")
        self.CValueAggregator.setValueTransformation("try:\n"
                                                             "    output(next(iter(values.values())))\n"
                                                             "except:\n"
                                                             "    output(0)")

        self.CValueAggregator.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCapture)


        return

    def myCallback(parameterName, newValue):
        print(1)
        return

    def receiveDataFromCapture(self, data):

        print(data)

        return