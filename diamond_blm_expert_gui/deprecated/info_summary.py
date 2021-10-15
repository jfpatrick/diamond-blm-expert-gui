########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem)
from PyQt5.QtCore import (QSize, Qt)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView)
import connection_custom

# OTHER IMPORTS

import sys
import os

########################################################
########################################################

class MyDisplay(CDisplay):

    #----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):

        return 'info_summary.ui'

    #----------------------------------------------#

    # init function
    def __init__(self, *args, **kwargs):

        print("Loading info_summary GUI file...")
        super().__init__(*args, **kwargs)
        self.setWindowTitle("BLM DIAMOND")

        print("Building the code-only widgets...")
        self.buildCodeWidgets()

        print("Handling signals and slots...")
        self.bindWidgets()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # create the info device table
        self.createTableFromDeviceList()

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        return

    #----------------------------------------------#

    # function that adds the items to the tree view
    def createTableFromDeviceList(self, device_list = ["SP.BA1.BLMDIAMOND.2", "SP.BA2.BLMDIAMOND.2", "SP.BA4.BLMDIAMOND.2", "SP.BA6.BLMDIAMOND.2"]):

        # set up the table
        #self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setRowCount(len(device_list))

        """
        for c in range(0, self.table.columnCount()):
            if c == 1:
                self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Interactive)
            else:
                self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        """

        # device
        column = 0
        row = 0
        for device in device_list:
            item = QTableWidgetItem(device)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, item)
            row += 1

        # device
        column = 1
        row = 0
        for device in device_list:
            item = QTableWidgetItem(device)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, item)
            row += 1

        # adjust rows and columns
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        return

    #----------------------------------------------#

########################################################
########################################################