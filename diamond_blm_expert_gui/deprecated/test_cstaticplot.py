########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import CDisplay
from PyQt5.QtGui import (QIcon, QColor)
from PyQt5.QtCore import (QSize, Qt)
from comrad import CStaticPlot
from comrad import PyDMChannelDataSource
from comrad import PointData, CurveData

# OTHER IMPORTS

import sys
import os


########################################################
########################################################

class MyDisplay(CDisplay):

    # ----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):
        return 'test_cstaticplot.ui'

    # ----------------------------------------------#

    # init function
    def __init__(self, *args, **kwargs):

        print("Loading UI file...")
        super().__init__(*args, **kwargs)

        self.pydm_channel_data_source_0 = PyDMChannelDataSource(channel_address="SP.BA1.BLMDIAMOND.2/Capture#rawBuf0", data_type_to_emit=CurveData, parent = self.CStaticPlot)
        self.pydm_channel_data_source_1 = PyDMChannelDataSource(channel_address="SP.BA1.BLMDIAMOND.2/Capture#rawBufFlags0", data_type_to_emit=CurveData, parent=self.CStaticPlot)

        self.pushButton_1.clicked.connect(self.button1Clicked)
        self.pushButton_2.clicked.connect(self.button2Clicked)

        return

    def button1Clicked(self):

        print("button 1 clicked")

        self.CStaticPlot.clear_items()
        self.CStaticPlot.addCurve(data_source=self.pydm_channel_data_source_0)
        self.pydm_channel_data_source_0.context_changed()

        return

    def button2Clicked(self):

        print("button 2 clicked")

        self.CStaticPlot.clear_items()
        self.CStaticPlot.addCurve(data_source=self.pydm_channel_data_source_1)
        self.pydm_channel_data_source_1.context_changed()

        return

########################################################
########################################################

