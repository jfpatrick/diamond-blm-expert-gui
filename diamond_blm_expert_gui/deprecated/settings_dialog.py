########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS
from comrad import CLineEdit
from comrad import (CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem)
from PyQt5.QtCore import (QSize, Qt)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea)
import connection_custom
import pyjapc

# OTHER IMPORTS

import sys
import os

########################################################
########################################################

class MyDisplay(CDisplay):

    #----------------------------------------------#

    # function to read the ui file
    def ui_filename(self):

        return 'settings_dialog.ui'

    #----------------------------------------------#

    # init function
    def __init__(self, *args, **kwargs):

        # create japc object
        #self.japc = pyjapc.PyJapc(incaAcceleratorName = None)
        self.japc = pyjapc.PyJapc()

        # set japc selector
        self.japc.setSelector("")

        print("Loading settings_dialog GUI file...")
        super().__init__(*args, **kwargs)
        self.setWindowTitle("BLM DIAMOND")

        print("Building the code-only widgets...")
        self.buildCodeWidgets()

        print("Handling signals and slots...")
        self.bindWidgets()

        # initialize getters
        #self.getFunction()



        all_data = self.japc.getParamInfo("dBLM.TEST4/BeamLossHistogramSetting", noPyConversion = True)
        print(dir(all_data))
        print()
        list_names = list(all_data.getNames())
        list_names.sort()
        print(list_names)

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # make the scroll bar of the get and set panel invisible
        sp_scroll_area_get_set = self.scrollArea_get_set.verticalScrollBar().sizePolicy()
        sp_scroll_area_get_set.setRetainSizeWhenHidden(True)
        self.scrollArea_get_set.verticalScrollBar().setSizePolicy(sp_scroll_area_get_set)
        self.scrollArea_get_set.verticalScrollBar().hide()

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # getters
        self.pushButton_get.clicked.connect(self.getFunction)

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        return

    #----------------------------------------------#

    # function that retrieves and displays the values of the properties
    def getFunction(self):

        print("GET PRESSED")

        device = "dBLM.TEST4"

        self.CLineEdit_BeamLossHistogram_BlmNTurn.setText(str(self.japc.getParam("{}/BeamLossHistogramSetting#blmNTurn".format(device))))
        self.CLineEdit_BeamLossHistogram_BlmThreshold0.setText(str(self.japc.getParam("{}/BeamLossHistogramSetting#blmThreshold0".format(device))))
        self.CLineEdit_BeamLossHistogram_BlmThreshold1.setText(str(self.japc.getParam("{}/BeamLossHistogramSetting#blmThreshold1".format(device))))
        self.CLineEdit_BeamLossIntegral_BaselineSub.setText(str(self.japc.getParam("{}/BeamLossIntegralSetting#baselineSub".format(device))))
        self.CLineEdit_BeamLossIntegral_TurnAvgCnt.setText(str(self.japc.getParam("{}/BeamLossIntegralSetting#turnAvgCnt".format(device))))
        #self.CLineEdit_Capture_NumCaptureSamples.setText(str(self.japc.getParam("{}/CaptureSetting#numCaptureSamples".format(device))))
        self.CLineEdit_Expert_FBDEPTH.setText(str(self.japc.getParam("{}/ExpertSetting#FBDEPTH".format(device))))
        self.CLineEdit_Expert_FBEXTRADEPTH0.setText(str(self.japc.getParam("{}/ExpertSetting#FBEXTRADEPTH0".format(device))))
        self.CLineEdit_Expert_FBEXTRADEPTH1.setText(str(self.japc.getParam("{}/ExpertSetting#FBEXTRADEPTH1".format(device))))
        self.CLineEdit_Expert_IrqConfig.setText(str(self.japc.getParam("{}/ExpertSetting#irqConfig".format(device))))
        self.CLineEdit_Expert_IrqLevel.setText(str(self.japc.getParam("{}/ExpertSetting#irqLevel".format(device))))
        self.CLineEdit_Expert_IrqMask.setText(str(self.japc.getParam("{}/ExpertSetting#irqMask".format(device))))
        self.CLineEdit_Expert_IrqVector.setText(str(self.japc.getParam("{}/ExpertSetting#irqVector".format(device))))
        self.CLineEdit_Expert_SYNCDELDEPTH.setText(str(self.japc.getParam("{}/ExpertSetting#SYNCDELDEPTH".format(device))))
        self.CLineEdit_ExpertTrigger_BSTDUMPTRIGGER.setText(str(self.japc.getParam("{}/ExpertTriggerSetting#BSTDUMPTRIGGER".format(device))))
        self.CLineEdit_ExpertTrigger_DUMPDETECTOR.setText(str(self.japc.getParam("{}/ExpertTriggerSetting#DUMPDETECTOR".format(device))))
        self.CLineEdit_ExpertTrigger_FREEZEDELAY.setText(str(self.japc.getParam("{}/ExpertTriggerSetting#FREEZEDELAY".format(device))))
        #self.CLineEdit_ExpertTrigger_NumCaptureSamples.setText(str(self.japc.getParam("{}/ExpertTriggerSetting#numCaptureSamples".format(device))))
        #self.CLineEdit_ExpertTrigger_RawSamplered.setText(str(self.japc.getParam("{}/ExpertTriggerSetting#rawSamplered".format(device))))
        self.CLineEdit_IntegralDataDist_IntDistLsbCut0.setText(str(self.japc.getParam("{}/IntegralDataDistSetting#intDistLsbCut0".format(device))))
        self.CLineEdit_IntegralDataDist_IntDistLsbCut1.setText(str(self.japc.getParam("{}/IntegralDataDistSetting#intDistLsbCut1".format(device))))
        self.CLineEdit_IntegralDataDist_IntDistOffset0.setText(str(self.japc.getParam("{}/IntegralDataDistSetting#intDistOffset0".format(device))))
        self.CLineEdit_IntegralDataDist_IntDistOffset1.setText(str(self.japc.getParam("{}/IntegralDataDistSetting#intDistOffset1".format(device))))
        self.CLineEdit_IntegralDataDist_TurnAvgCnt.setText(str(self.japc.getParam("{}/IntegralDataDistSetting#turnAvgCnt".format(device))))
        self.CLineEdit_RawDataDist_RawDistLsbCut0.setText(str(self.japc.getParam("{}/RawDataDistributionSetting#rawDistLsbCut0".format(device))))
        self.CLineEdit_RawDataDist_RawDistLsbCut1.setText(str(self.japc.getParam("{}/RawDataDistributionSetting#rawDistLsbCut1".format(device))))
        self.CLineEdit_RawDataDist_RawDistOffset0.setText(str(self.japc.getParam("{}/RawDataDistributionSetting#rawDistOffset0".format(device))))
        self.CLineEdit_RawDataDist_RawDistOffset1.setText(str(self.japc.getParam("{}/RawDataDistributionSetting#rawDistOffset1".format(device))))
        self.CLineEdit_RawDataDist_TurnAvgCnt.setText(str(self.japc.getParam("{}/RawDataDistributionSetting#turnAvgCnt".format(device))))
        self.CLineEdit_TurnLossMeasurement_TurnTrackCnt.setText(str(self.japc.getParam("{}/TurnLossMeasurementSetting#turnTrackCnt".format(device))))

        return

    #----------------------------------------------#

    # function that sets the values into the properties
    def setFunction(self):

        print("SET PRESSED")

        device = "dBLM.TEST4"

        #print(self.CLineEdit_BeamLossHistogram_BlmNTurn.text())
        #self.japc.setParam("{}/BeamLossHistogramSetting#blmNTurn".format(device), self.CLineEdit_BeamLossHistogram_BlmNTurn.text())
        self.japc.setParam("dBLM.TEST4/BeamLossHistogramSetting", {"blmNTurn":9991, "blmThreshold0":9999, "blmThreshold1":9999})

        return

    #----------------------------------------------#

########################################################
########################################################