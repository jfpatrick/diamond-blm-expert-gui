########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, CApplication, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource, CContextFrame, CStaticPlot, CLabel, CCommandButton)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QBrush)
from PyQt5.QtCore import (QSize, Qt)
from PyQt5.QtWidgets import (QSizePolicy, QWidget, QHBoxLayout, QHBoxLayout, QVBoxLayout, QSpacerItem, QFrame, QGridLayout, QLabel, QTabWidget)

# OTHER IMPORTS

import sys
import os
import numpy as np
from copy import deepcopy
import jpype as jp
from time import sleep
import json

########################################################
########################################################

# GLOBALS

UI_FILENAME = "main_auto.ui"
CAPTURE_TAB = True

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

        # retrieve the pyccda json info file
        self.readPyCCDAJsonFile()

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # import cern package for handling exceptions
        self.cern = jp.JPackage("cern")

        # set current device
        self.current_device = "dBLM.TEST4"
        self.current_accelerator = "LHC"
        self.LoadDeviceFromTxtPremain()

        # set current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())

        # order the property list
        self.property_list.sort()

        # input the exception list
        self.exception_list = ["Capture", "GeneralInformation"]

        # input the command list
        self.command_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["command"].keys())

        # order the command list
        self.command_list.sort()

        # remove typical command substrings
        self.command_list_substrings_removed = deepcopy(self.command_list)
        for index_command in range(0, len(self.command_list_substrings_removed)):
            self.command_list_substrings_removed[index_command] = self.command_list_substrings_removed[index_command].replace("Reset", "")
            self.command_list_substrings_removed[index_command] = self.command_list_substrings_removed[index_command].replace("Start", "")
            self.command_list_substrings_removed[index_command] = self.command_list_substrings_removed[index_command].replace("Stop", "")
            self.command_list_substrings_removed[index_command] = self.command_list_substrings_removed[index_command].replace("Trigger", "")

        # check dict for the capture tab
        self.current_check_dict = {"ts0": True, "ts1": True, "peaks0": True, "peaks1": True}

        # initialize the field dictionary
        self.field_dict = {}

        # load the gui, build the widgets and handle the signals
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("DIAMOND BLM MAIN")
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # only if CAPTURE_TAB is enabled (use this for debugging)
        if CAPTURE_TAB and "dBLM.TEST" not in self.current_device:

            # init custom PyDM channels for the Capture plots
            self.pydm_channel_capture_rawbuffer_0 = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
            self.pydm_channel_capture_rawbuffer_0_FFT = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer0_FFT", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)
            self.pydm_channel_capture_rawbuffer_1 = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer1", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1)
            self.pydm_channel_capture_rawbuffer_1_FFT = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#rawBuffer1_FFT", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1_FFT)
            self.pydm_channel_capture_rawbuffer_0_timestamps = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#flags0_five_six", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0)
            self.pydm_channel_capture_rawbuffer_1_timestamps = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#flags1_five_six", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1)
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0_xplots", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf0_FFT)
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones = PyDMChannelDataSource(channel_address="UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1_xplots", data_type_to_emit=CurveData, parent=self.CStaticPlot_Capture_rawBuf1_FFT)

        # load and set the channels
        print("{} - Setting all channels...".format(UI_FILENAME))
        self.setChannels()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # initialize widget dicts
        self.tabDict = {}
        self.layoutDict = {}
        self.labelDict = {}
        self.clabelDict = {}
        self.commandButtonDict = {}
        self.contextFrameDict = {}
        self.staticPlotDict = {}
        self.frameDict = {}

        # iterate over the property tabs
        for property in self.property_list:

            # custom tab
            if str(property) in self.exception_list:

                # CAPTURE TAB - change cursors of CRelatedDisplayButton to normal ArrowCursor
                self.CRelatedDisplayButton_rawBuf0.setCursor(QCursor(Qt.ArrowCursor))
                self.CRelatedDisplayButton_rawBuf0_FFT.setCursor(QCursor(Qt.ArrowCursor))
                self.CRelatedDisplayButton_rawBuf1.setCursor(QCursor(Qt.ArrowCursor))
                self.CRelatedDisplayButton_rawBuf1_FFT.setCursor(QCursor(Qt.ArrowCursor))

                # CAPTURE TAB - make push buttons invisible just to make the grid look nicer
                sp_retain0 = self.pushButton_invisible_0.sizePolicy()
                sp_retain0.setRetainSizeWhenHidden(True)
                self.pushButton_invisible_0.setSizePolicy(sp_retain0)
                self.pushButton_invisible_0.hide()
                sp_retain1 = self.pushButton_invisible_1.sizePolicy()
                sp_retain1.setRetainSizeWhenHidden(True)
                self.pushButton_invisible_1.setSizePolicy(sp_retain1)
                self.pushButton_invisible_1.hide()

                pass

            # generic tab
            else:

                # init tab
                self.tabDict["{}".format(property)] = QWidget()
                self.tabDict["{}".format(property)].setObjectName("tab_{}".format(property))

                # horizontal layout of the tab
                self.layoutDict["horizontal_layout_tab_{}".format(property)] = QHBoxLayout(self.tabDict["{}".format(property)])
                self.layoutDict["horizontal_layout_tab_{}".format(property)].setObjectName("horizontal_layout_tab_{}".format(property))

                # context frame of the CStaticPlot area
                self.contextFrameDict["CStaticPlot_area_{}".format(property)] = CContextFrame(self.tabDict["{}".format(property)])
                self.contextFrameDict["CStaticPlot_area_{}".format(property)].setObjectName("CStaticPlot_area_{}".format(property))
                self.contextFrameDict["CStaticPlot_area_{}".format(property)].inheritSelector = False
                self.contextFrameDict["CStaticPlot_area_{}".format(property)].selector = self.current_selector

                # vertical layout of the CStaticPlot area
                self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)] = QVBoxLayout(self.contextFrameDict["CStaticPlot_area_{}".format(property)])
                self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)].setObjectName("vertical_layout_tab_CStaticplot_area_{}".format(property))
                self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)].setSpacing(12)

                # context frame of the information area
                self.contextFrameDict["CContextFrame_information_area_{}".format(property)] = CContextFrame(self.tabDict["{}".format(property)])
                self.contextFrameDict["CContextFrame_information_area_{}".format(property)].setObjectName("CContextFrame_information_area_{}".format(property))
                self.contextFrameDict["CContextFrame_information_area_{}".format(property)].inheritSelector = False
                self.contextFrameDict["CContextFrame_information_area_{}".format(property)].selector = self.current_selector

                # vertical layout of the information area
                self.layoutDict["vertical_layout_tab_information_area_{}".format(property)] = QVBoxLayout(self.contextFrameDict["CContextFrame_information_area_{}".format(property)])
                self.layoutDict["vertical_layout_tab_information_area_{}".format(property)].setObjectName("vertical_layout_tab_information_area_{}".format(property))

                # top spacer
                spacerItem_top = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
                self.layoutDict["vertical_layout_tab_information_area_{}".format(property)].addItem(spacerItem_top)

                # frame for the generic table
                self.frameDict["frame_information_area_{}".format(property)] = QFrame(self.contextFrameDict["CContextFrame_information_area_{}".format(property)])
                self.frameDict["frame_information_area_{}".format(property)].setObjectName("frame_information_area_{}".format(property))
                self.frameDict["frame_information_area_{}".format(property)].setFrameShape(QFrame.NoFrame)
                self.frameDict["frame_information_area_{}".format(property)].setFrameShadow(QFrame.Plain)

                # grid layout for the generic table
                self.layoutDict["grid_layout_tab_information_area_{}".format(property)] = QGridLayout(self.frameDict["frame_information_area_{}".format(property)])
                self.layoutDict["grid_layout_tab_information_area_{}".format(property)].setObjectName("grid_layout_tab_information_area_{}".format(property))

                # retrieve the field names
                self.field_dict["{}".format(property)] = {}
                self.field_dict["{}".format(property)]["fields_that_are_arrays"] = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["array"].keys())
                self.field_dict["{}".format(property)]["fields_that_are_not_arrays"] = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"][property]["scalar"].keys())

                # sort the lists
                self.field_dict["{}".format(property)]["fields_that_are_arrays"].sort()
                self.field_dict["{}".format(property)]["fields_that_are_not_arrays"].sort()

                # manually remove indexes and compressed fields for AcquisitionHistogram
                if property == "AcquisitionHistogram":
                    to_remove = ["blmbuf0_compressed", "blmbuf1_compressed", "blmbuf0_indexes", "blmbuf1_indexes"]
                    self.field_dict["{}".format(property)]["fields_that_are_arrays"] = list(set(self.field_dict["{}".format(property)]["fields_that_are_arrays"]).difference(to_remove))
                elif property == "AcquisitionTurnLoss":
                    to_remove = ["turnLossBuf0_compressed", "turnLossBuf1_compressed", "turnLossBuf0_indexes", "turnLossBuf1_indexes"]
                    self.field_dict["{}".format(property)]["fields_that_are_arrays"] = list(set(self.field_dict["{}".format(property)]["fields_that_are_arrays"]).difference(to_remove))

                # add the top title labels (the first row of the table)
                row = 0

                # set fields label (column == 0)
                column = 0
                self.labelDict["{}_{}".format(property, "title_fields")] = QLabel(self.frameDict["frame_information_area_{}".format(property)])
                self.labelDict["{}_{}".format(property, "title_fields")].setObjectName("label_{}_{}".format(property, "title_fields"))
                self.labelDict["{}_{}".format(property, "title_fields")].setMinimumSize(QSize(0, 30))
                self.labelDict["{}_{}".format(property, "title_fields")].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format(property, "title_fields")].setText("{}".format("Fields"))
                self.labelDict["{}_{}".format(property, "title_fields")].setStyleSheet("background-color: rgb(210, 210, 210);")
                self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.labelDict["{}_{}".format(property, "title_fields")], row, column, 1, 1)

                # set values label (column == 1)
                column = 1
                self.labelDict["{}_{}".format(property, "title_values")] = QLabel(self.frameDict["frame_information_area_{}".format(property)])
                self.labelDict["{}_{}".format(property, "title_values")].setObjectName("label_{}_{}".format(property, "title_values"))
                self.labelDict["{}_{}".format(property, "title_values")].setMinimumSize(QSize(0, 30))
                self.labelDict["{}_{}".format(property, "title_values")].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format(property, "title_values")].setText("{}".format("Values"))
                self.labelDict["{}_{}".format(property, "title_values")].setStyleSheet("background-color: rgb(210, 210, 210);")
                self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.labelDict["{}_{}".format(property, "title_values")], row, column, 1, 1)

                # add the labels to the table
                row = 1
                for field in self.field_dict["{}".format(property)]["fields_that_are_not_arrays"]:

                    # set label (column == 0)
                    column = 0
                    self.labelDict["{}_{}".format(property, field)] = QLabel(self.frameDict["frame_information_area_{}".format(property)])
                    self.labelDict["{}_{}".format(property, field)].setObjectName("label_{}_{}".format(property, field))
                    self.labelDict["{}_{}".format(property, field)].setMinimumSize(QSize(0, 30))
                    self.labelDict["{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["{}_{}".format(property, field)].setText("{}".format(field))
                    self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.labelDict["{}_{}".format(property, field)], row, column, 1, 1)

                    # set clabel (column == 1)
                    column = 1
                    self.clabelDict["{}_{}".format(property, field)] = CLabel(self.frameDict["frame_information_area_{}".format(property)])
                    self.clabelDict["{}_{}".format(property, field)].setObjectName("clabel_{}_{}".format(property, field))
                    self.clabelDict["{}_{}".format(property, field)].setProperty("type", 1)
                    self.clabelDict["{}_{}".format(property, field)].setMinimumSize(QSize(0, 30))
                    self.clabelDict["{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.clabelDict["{}_{}".format(property, field)].setText("Null")
                    self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.clabelDict["{}_{}".format(property, field)], row, column, 1, 1)

                    # get the next field
                    row += 1

                # add the commands to the table
                for index_command, command_substring in enumerate(self.command_list_substrings_removed):

                    # check if the command has to do with the property tab
                    if command_substring in property:

                        # set the command
                        command = self.command_list[index_command]

                        # context frame and layout of the command button (column == 0)
                        self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)] = CContextFrame(self.frameDict["frame_information_area_{}".format(property)])
                        self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)].setObjectName("CContextFrame_command_button_column_0_{}_{}".format(property, command))
                        self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)].inheritSelector = False
                        self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)].selector = ""
                        self.layoutDict["layout_command_button_{}".format(property, command)] = QVBoxLayout(self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)])
                        self.layoutDict["layout_command_button_{}".format(property, command)].setObjectName("layout_command_button_{}".format(property, command))
                        self.layoutDict["layout_command_button_{}".format(property, command)].setContentsMargins(0, 0, 0, 0)

                        # set label (column == 0)
                        column = 0
                        self.labelDict["{}_{}".format(property, command)] = QLabel(self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)])
                        self.labelDict["{}_{}".format(property, command)].setObjectName("label_{}_{}".format(property, command))
                        self.labelDict["{}_{}".format(property, command)].setMinimumSize(QSize(0, 30))
                        self.labelDict["{}_{}".format(property, command)].setAlignment(Qt.AlignCenter)
                        self.labelDict["{}_{}".format(property, command)].setText("{}".format(command))
                        self.layoutDict["layout_command_button_{}".format(property, command)].addWidget(self.labelDict["{}_{}".format(property, command)])
                        self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)], row, column, 1, 1)

                        # context frame and layout of the command button (column == 1)
                        self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)] = CContextFrame(self.frameDict["frame_information_area_{}".format(property)])
                        self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)].setObjectName("CContextFrame_command_button_column_1_{}_{}".format(property, command))
                        self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)].inheritSelector = False
                        self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)].selector = ""
                        self.layoutDict["layout_command_button_{}".format(property, command)] = QVBoxLayout(self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)])
                        self.layoutDict["layout_command_button_{}".format(property, command)].setObjectName("layout_command_button_{}".format(property, command))
                        self.layoutDict["layout_command_button_{}".format(property, command)].setContentsMargins(0, 0, 0, 0)

                        # set ccommandbutton (column == 1)
                        column = 1
                        self.commandButtonDict["{}_{}".format(property, command)] = CCommandButton(self.contextFrameDict["CContextFrame_command_button_column_0_{}_{}".format(property, command)])
                        self.commandButtonDict["{}_{}".format(property, command)].setObjectName("ccommandbutton_{}_{}".format(property, command))
                        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                        sizePolicy.setHorizontalStretch(0)
                        sizePolicy.setVerticalStretch(0)
                        sizePolicy.setHeightForWidth(self.commandButtonDict["{}_{}".format(property, command)].sizePolicy().hasHeightForWidth())
                        self.commandButtonDict["{}_{}".format(property, command)].setSizePolicy(sizePolicy)
                        self.commandButtonDict["{}_{}".format(property, command)].setText("{}".format(" Run"))
                        self.commandButtonDict["{}_{}".format(property, command)].setIcon(QIcon("../icons/command.png"))
                        self.commandButtonDict["{}_{}".format(property, command)].setMinimumSize(QSize(0, 30))
                        self.commandButtonDict["{}_{}".format(property, command)].channel = "{}/{}".format(self.current_device, command)
                        self.layoutDict["layout_command_button_{}".format(property, command)].addWidget(self.commandButtonDict["{}_{}".format(property, command)])
                        self.layoutDict["grid_layout_tab_information_area_{}".format(property)].addWidget(self.contextFrameDict["CContextFrame_command_button_column_1_{}_{}".format(property, command)], row, column, 1, 1)

                        # get the next command
                        row += 1

                # setup a frame to host the acq timestamp and cycle name header fields
                self.frameDict["frame_for_header_data_{}".format(property)] = QFrame(self.contextFrameDict["CStaticPlot_area_{}".format(property)])
                self.frameDict["frame_for_header_data_{}".format(property)].setObjectName("frame_for_header_data_{}".format(property))
                self.frameDict["frame_for_header_data_{}".format(property)].setFrameShape(QFrame.NoFrame)
                self.frameDict["frame_for_header_data_{}".format(property)].setFrameShadow(QFrame.Plain)

                # setup the horizontal layout of the header frame
                self.layoutDict["horizontal_layout_header_data_{}".format(property)] = QHBoxLayout(self.frameDict["frame_for_header_data_{}".format(property)])
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].setObjectName("horizontal_layout_header_data_{}".format(property))
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].setContentsMargins(0, 0, 0, 0)

                # left spacer
                spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].addItem(spacerItem)

                # add the acq timestamp on top of the cstaticplots
                self.clabelDict["{}_AcqTimestamp".format(property)] = CLabel(self.frameDict["frame_for_header_data_{}".format(property)])
                self.clabelDict["{}_AcqTimestamp".format(property)].setObjectName("{}_AcqTimestamp".format(property))
                self.clabelDict["{}_AcqTimestamp".format(property)].setProperty("type", 2)
                self.clabelDict["{}_AcqTimestamp".format(property)].setTextFormat(Qt.RichText)
                self.clabelDict["{}_AcqTimestamp".format(property)].setText("<b>acqStamp:</b> Null  ")
                self.clabelDict["{}_AcqTimestamp".format(property)].setAlignment(Qt.AlignCenter)
                minWidth = self.clabelDict["{}_AcqTimestamp".format(property)].fontMetrics().boundingRect(self.clabelDict["{}_AcqTimestamp".format(property)].text()).width()
                self.clabelDict["{}_AcqTimestamp".format(property)].setMinimumSize(QSize(minWidth, 0))
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].addWidget(self.clabelDict["{}_AcqTimestamp".format(property)])

                # add the cycle name on top of the cstaticplots
                self.clabelDict["{}_CycleName".format(property)] = CLabel(self.frameDict["frame_for_header_data_{}".format(property)])
                self.clabelDict["{}_CycleName".format(property)].setObjectName("{}_CycleName".format(property))
                self.clabelDict["{}_CycleName".format(property)].setProperty("type", 2)
                self.clabelDict["{}_CycleName".format(property)].setTextFormat(Qt.RichText)
                self.clabelDict["{}_CycleName".format(property)].setText("<b>cycleName:</b> Null  ")
                self.clabelDict["{}_CycleName".format(property)].setAlignment(Qt.AlignCenter)
                minWidth = self.clabelDict["{}_CycleName".format(property)].fontMetrics().boundingRect(self.clabelDict["{}_CycleName".format(property)].text()).width()
                self.clabelDict["{}_CycleName".format(property)].setMinimumSize(QSize(minWidth, 0))
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].addWidget(self.clabelDict["{}_CycleName".format(property)])

                # right spacer
                spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
                self.layoutDict["horizontal_layout_header_data_{}".format(property)].addItem(spacerItem)

                # add the header to the vertical CStaticplot area
                self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)].addWidget(self.frameDict["frame_for_header_data_{}".format(property)])

                # add the plots
                for field in self.field_dict["{}".format(property)]["fields_that_are_arrays"]:
                    self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)] = CStaticPlot(self.contextFrameDict["CStaticPlot_area_{}".format(property)])
                    self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)].setObjectName("CStaticPlot_{}_{}".format(property, field))
                    self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)].addWidget(self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)])

                # add the plotting area to the layout
                self.layoutDict["horizontal_layout_tab_{}".format(property)].addWidget(self.contextFrameDict["CStaticPlot_area_{}".format(property)])

                # add the frame to the vertical layout of the information area
                self.layoutDict["vertical_layout_tab_information_area_{}".format(property)].addWidget(self.frameDict["frame_information_area_{}".format(property)])

                # bottom spacer
                spacerItem_bottom = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
                self.layoutDict["vertical_layout_tab_information_area_{}".format(property)].addItem(spacerItem_bottom)

                # add the information context frame to the horizontal layout of the tab and adjust the dimensions
                self.layoutDict["horizontal_layout_tab_{}".format(property)].addWidget(self.contextFrameDict["CContextFrame_information_area_{}".format(property)])
                self.layoutDict["horizontal_layout_tab_{}".format(property)].setStretch(0, 79)
                self.layoutDict["horizontal_layout_tab_{}".format(property)].setStretch(1, 21)

                # finally add the tab to the tabWidget panel
                self.tabWidget.addTab(self.tabDict["{}".format(property)], "{}".format(property))

                # move the last tab to the left
                self.tabWidget.tabBar().moveTab(self.tabWidget.count(), 0)

        # reorder tabs alphabetically with the bubble sort algorithm
        for tab_i in range(0, self.tabWidget.count()-1):
            for tab_j in range(0, self.tabWidget.count()-tab_i-1):
                if self.tabWidget.tabText(tab_j) > self.tabWidget.tabText(tab_j+1):
                    self.tabWidget.tabBar().moveTab(tab_j, tab_j+1)

        # get Capture tab index
        index_of_capture_tab = 0
        for tab_i in range(0, self.tabWidget.count()-1):
            if self.tabWidget.tabText(tab_i) == "Capture":
                index_of_capture_tab = tab_i
                break

        # set the focus on the Capture tab
        self.tabWidget.setCurrentIndex(tab_i)

        # obtain the tab names
        self.tab_names = [self.tabWidget.tabText(tab_i) for tab_i in range(0, self.tabWidget.count())]

        # disable Capture buttons if CAPTURE_TAB is disabled
        if CAPTURE_TAB and "dBLM.TEST" not in self.current_device:
            self.CRelatedDisplayButton_rawBuf0.setEnabled(True)
            self.CRelatedDisplayButton_rawBuf1.setEnabled(True)
            self.CRelatedDisplayButton_rawBuf0_FFT.setEnabled(True)
            self.CRelatedDisplayButton_rawBuf1_FFT.setEnabled(True)
            self.checkBox_turns_0.setEnabled(True)
            self.checkBox_turns_1.setEnabled(True)
            self.checkBox_peaks_0.setEnabled(True)
            self.checkBox_peaks_1.setEnabled(True)
            self.CLabel_acqStamp_Capture_0.setEnabled(True)
            self.CLabel_acqStamp_Capture_1.setEnabled(True)
            self.CLabel_cycleName_Capture_0.setEnabled(True)
            self.CLabel_cycleName_Capture_1.setEnabled(True)
            self.CLabel_Overtones0_1.setEnabled(True)
            self.CLabel_Overtones0_2.setEnabled(True)
            self.CLabel_Overtones0_3.setEnabled(True)
            self.CLabel_Overtones0_4.setEnabled(True)
            self.CLabel_Overtones0_5.setEnabled(True)
            self.CLabel_Overtones0_6.setEnabled(True)
            self.CLabel_Overtones0_7.setEnabled(True)
            self.CLabel_Overtones1_1.setEnabled(True)
            self.CLabel_Overtones1_2.setEnabled(True)
            self.CLabel_Overtones1_3.setEnabled(True)
            self.CLabel_Overtones1_4.setEnabled(True)
            self.CLabel_Overtones1_5.setEnabled(True)
            self.CLabel_Overtones1_6.setEnabled(True)
            self.CLabel_Overtones1_7.setEnabled(True)
        else:
            self.CRelatedDisplayButton_rawBuf0.setEnabled(False)
            self.CRelatedDisplayButton_rawBuf1.setEnabled(False)
            self.CRelatedDisplayButton_rawBuf0_FFT.setEnabled(False)
            self.CRelatedDisplayButton_rawBuf1_FFT.setEnabled(False)
            self.checkBox_turns_0.setEnabled(False)
            self.checkBox_turns_1.setEnabled(False)
            self.checkBox_peaks_0.setEnabled(False)
            self.checkBox_peaks_1.setEnabled(False)
            self.CLabel_acqStamp_Capture_0.setEnabled(False)
            self.CLabel_acqStamp_Capture_1.setEnabled(False)
            self.CLabel_cycleName_Capture_0.setEnabled(False)
            self.CLabel_cycleName_Capture_1.setEnabled(False)
            self.CLabel_Overtones0_1.setEnabled(False)
            self.CLabel_Overtones0_2.setEnabled(False)
            self.CLabel_Overtones0_3.setEnabled(False)
            self.CLabel_Overtones0_4.setEnabled(False)
            self.CLabel_Overtones0_5.setEnabled(False)
            self.CLabel_Overtones0_6.setEnabled(False)
            self.CLabel_Overtones0_7.setEnabled(False)
            self.CLabel_Overtones1_1.setEnabled(False)
            self.CLabel_Overtones1_2.setEnabled(False)
            self.CLabel_Overtones1_3.setEnabled(False)
            self.CLabel_Overtones1_4.setEnabled(False)
            self.CLabel_Overtones1_5.setEnabled(False)
            self.CLabel_Overtones1_6.setEnabled(False)
            self.CLabel_Overtones1_7.setEnabled(False)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # checkbox for enabling and disabling turns of rawbuf0
        self.checkBox_turns_0.stateChanged.connect(self.pleaseShowTurns0)

        # checkbox for enabling and disabling turns of rawbuf1
        self.checkBox_turns_1.stateChanged.connect(self.pleaseShowTurns1)

        # checkbox for enabling and disabling peaks of rawbuf0_FFT
        self.checkBox_peaks_0.stateChanged.connect(self.pleaseShowPeaks0)

        # checkbox for enabling and disabling peaks of rawbuf1_FFT
        self.checkBox_peaks_1.stateChanged.connect(self.pleaseShowPeaks1)

        # write device into txt for fullscreen mode
        self.CRelatedDisplayButton_rawBuf0.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf1.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf0_FFT.clicked.connect(self.writeDeviceIntoTxtForFullScreen)
        self.CRelatedDisplayButton_rawBuf1_FFT.clicked.connect(self.writeDeviceIntoTxtForFullScreen)

        # selector signal
        self.app.main_window.window_context.selectorChanged.connect(self.selectorWasChanged)

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

        # iterate over the property tabs
        for property in self.property_list:

            # generic tab
            if str(property) not in self.exception_list:

                # update the contexts
                self.contextFrameDict["CContextFrame_information_area_{}".format(property)].selector = self.current_selector
                self.contextFrameDict["CStaticPlot_area_{}".format(property)].selector = self.current_selector

                self.clabelDict["{}_AcqTimestamp".format(property)].context_changed()
                self.clabelDict["{}_CycleName".format(property)].context_changed()

        return

    #----------------------------------------------#

    # function that reads from the json file generated by the pyccda script
    def readPyCCDAJsonFile(self):

        # read pyccda info file
        if os.path.exists("aux_jsons/pyccda_sps.json"):
            with open("aux_jsons/pyccda_sps.json") as f:
                self.pyccda_dictionary = json.load(f)

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxtPremain(self):

        # read current device
        if os.path.exists("aux_txts/current_device_premain.txt"):
            with open("aux_txts/current_device_premain.txt", "r") as f:
                self.current_device = f.read()

        # read current accelerator
        if os.path.exists("aux_txts/current_accelerator_premain.txt"):
            with open("aux_txts/current_accelerator_premain.txt", "r") as f:
                self.current_accelerator = f.read()

        return

    #----------------------------------------------#

    # function that writes the device name into a txt file
    def writeDeviceIntoTxtForFullScreen(self):

        # create the dir in case it does not exist
        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        # write the file
        with open("aux_txts/current_device.txt", "w") as f:
            f.write(str(self.current_device))

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf0
    def pleaseShowTurns0(self, state):

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns0 button checked...".format(UI_FILENAME))
            self.current_check_dict["ts0"] = True
            self.CStaticPlot_Capture_rawBuf0.clear_items()
            self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            if self.current_check_dict["ts0"]:
                self.CStaticPlot_Capture_rawBuf0.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0)
            self.pydm_channel_capture_rawbuffer_0.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

        # if it is not checked
        else:

            # remove the flags
            print("{} - Turns0 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["ts0"] = False
            self.CStaticPlot_Capture_rawBuf0.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps)
            self.pydm_channel_capture_rawbuffer_0.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf1
    def pleaseShowTurns1(self, state):

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf1.plotItem.setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns1 button checked...".format(UI_FILENAME))
            self.current_check_dict["ts1"] = True
            self.CStaticPlot_Capture_rawBuf1.clear_items()
            self.CStaticPlot_Capture_rawBuf1.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps)
            if self.current_check_dict["ts1"]:
                self.CStaticPlot_Capture_rawBuf1.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1)
            self.pydm_channel_capture_rawbuffer_1.context_changed()
            self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

        # if it is not checked
        else:

            # remove the flags
            print("{} - Turns1 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["ts1"] = False
            self.CStaticPlot_Capture_rawBuf1.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps)
            self.pydm_channel_capture_rawbuffer_1.context_changed()
            self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

        # reset clip to view to avoid errors
        self.CStaticPlot_Capture_rawBuf1.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf0_FFT
    def pleaseShowPeaks0(self, state):

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new peaks
            print("{} - Peaks0 button checked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = True
            self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
            self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT)
            if self.current_check_dict["peaks0"]:
                self.CStaticPlot_Capture_rawBuf0_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        # if it is not checked
        else:

            # remove the peaks
            print("{} - Peaks0 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = False
            self.CStaticPlot_Capture_rawBuf0_FFT.removeItem(
                self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf1_FFT
    def pleaseShowPeaks1(self, state):

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf1_FFT.plotItem.setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new peaks
            print("{} - Peaks1 button checked...".format(UI_FILENAME))
            self.current_check_dict["peaks1"] = True
            self.CStaticPlot_Capture_rawBuf1_FFT.clear_items()
            self.CStaticPlot_Capture_rawBuf1_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT)
            if self.current_check_dict["peaks1"]:
                self.CStaticPlot_Capture_rawBuf1_FFT.addItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()

        # if it is not checked
        else:

            # remove the peaks
            print("{} - Peaks1 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["peaks1"] = False
            self.CStaticPlot_Capture_rawBuf1_FFT.removeItem(self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones)
            self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()

        # reset clip to view to avoid errors
        # self.CStaticPlot_Capture_rawBuf1_FFT.plotItem.setClipToView(True)

        return

    #----------------------------------------------#

    # function that set the right channels for each widget depending on the selected device
    def setChannels(self):

        # set channels for the generic tabs
        for property in self.property_list:

            # make sure the tab was created
            if property in self.tab_names and property in self.field_dict:

                # set up the acq timestamp
                self.clabelDict["{}_AcqTimestamp".format(property)].channel = "{}/{}#{}".format(self.current_device, property, "acqStamp")
                self.clabelDict["{}_AcqTimestamp".format(property)].setValueTransformation("output(\'<b>acqStamp:</b> {} UTC  \'.format(new_val))")
                self.clabelDict["{}_CycleName".format(property)].channel = "{}/{}#{}".format(self.current_device, property, "cycleName")
                self.clabelDict["{}_CycleName".format(property)].setValueTransformation("output(\'<b>cycleName:</b> {}\'.format(new_val))")

                # iterate over the non-plot fields
                for field in self.field_dict["{}".format(property)]["fields_that_are_not_arrays"]:

                    # set the channel with a normal CLabel.channel allocation
                    self.clabelDict["{}_{}".format(property, field)].channel = "{}/{}#{}".format(self.current_device, property, field)

                # iterate over the plot fields
                for field in self.field_dict["{}".format(property)]["fields_that_are_arrays"]:

                    # set the channel with an addCurve update
                    self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)].addCurve(data_source = "{}/{}#{}".format(self.current_device, property, field))

                    # set the title of the plot
                    self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_plot_title("{}".format(field))

                    # the axis have to be added manually by hand
                    if "AcquisitionHistogram" == property:
                        self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_axis_labels("{\"left\": \"threshold crossings\", \"top\": \"\", \"right\": \"\", \"bottom\": \"bins\"}")
                    elif "AcquisitionIntegral" == property:
                       self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_axis_labels("{\"left\": \"loss\", \"top\": \"\", \"right\": \"\", \"bottom\": \"bunch number\"}")
                    elif "AcquisitionIntegralDist" == property:
                       self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_axis_labels("{\"left\": \"distribution\", \"top\": \"\", \"right\": \"\", \"bottom\": \"value\"}")
                    elif "AcquisitionRawDist" == property:
                       self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_axis_labels("{\"left\": \"distribution\", \"top\": \"\", \"right\": \"\", \"bottom\": \"value\"}")
                    elif "AcquisitionTurnLoss" == property:
                       self.staticPlotDict["CStaticPlot_{}_{}".format(property, field)]._set_axis_labels("{\"left\": \"loss\", \"top\": \"\", \"right\": \"\", \"bottom\": \"turn number\"}")

        # set channels for the GeneralInformation tab
        self.CLabel_GeneralInformation_AcqStamp.channel = self.current_device + "/" + "GeneralInformation#acqStamp"
        self.CLabel_GeneralInformation_AutoGain.channel = self.current_device + "/" + "GeneralInformation#AutoGain"
        self.CLabel_GeneralInformation_BeamMomentum.channel = self.current_device + "/" + "GeneralInformation#BeamMomentum"
        self.CLabel_GeneralInformation_BoardId.channel = self.current_device + "/" + "GeneralInformation#BoardId"
        self.CLabel_GeneralInformation_BstShift.channel = self.current_device + "/" + "GeneralInformation#BstShift"
        self.CLabel_GeneralInformation_BunchSample.channel = self.current_device + "/" + "GeneralInformation#BunchSample"
        self.CLabel_GeneralInformation_FpgaCompilation.channel = self.current_device + "/" + "GeneralInformation#FpgaCompilation"
        self.CLabel_GeneralInformation_FpgaFirmware.channel = self.current_device + "/" + "GeneralInformation#FpgaFirmware"
        self.CLabel_GeneralInformation_FpgaStatus.channel = self.current_device + "/" + "GeneralInformation#FpgaStatus"
        self.CLabel_GeneralInformation_MachineId.channel = self.current_device + "/" + "GeneralInformation#MachineId"
        self.CLabel_GeneralInformation_MonitorNames.channel = self.current_device + "/" + "GeneralInformation#monitorNames"
        self.CLabel_GeneralInformation_TurnBc.channel = self.current_device + "/" + "GeneralInformation#TurnBc"
        self.CLabel_GeneralInformation_TurnDropped.channel = self.current_device + "/" + "GeneralInformation#TurnDropped"
        self.CLabel_GeneralInformation_TurnSample.channel = self.current_device + "/" + "GeneralInformation#TurnSample"

        # only if CAPTURE_TAB is enabled (use this for debugging)
        if CAPTURE_TAB and "dBLM.TEST" not in self.current_device:

            # set up the acqStamp and cycleName for the rabuf0
            self.CContextFrame_acqStamp_Capture_0.inheritSelector = False
            self.CContextFrame_acqStamp_Capture_0.selector = ""
            self.CLabel_acqStamp_Capture_0.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#acqStamp"
            self.CLabel_acqStamp_Capture_0.setValueTransformation("output(\'<b>acqStamp:</b> {} UTC  \'.format(new_val))")
            self.CLabel_cycleName_Capture_0.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#cycleName"
            self.CLabel_cycleName_Capture_0.setValueTransformation("output(\'<b>cycleName:</b> {}\'.format(new_val))")

            # set up the acqStamp and cycleName for the rabuf1
            self.CContextFrame_acqStamp_Capture_1.inheritSelector = False
            self.CContextFrame_acqStamp_Capture_1.selector = ""
            self.CLabel_acqStamp_Capture_1.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#acqStamp"
            self.CLabel_acqStamp_Capture_1.setValueTransformation("output(\'<b>acqStamp:</b> {} UTC  \'.format(new_val))")
            self.CLabel_cycleName_Capture_1.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#cycleName"
            self.CLabel_cycleName_Capture_1.setValueTransformation("output(\'<b>cycleName:</b> {}\'.format(new_val))")

            # set channels for Capture tab rawBuffer0
            self.CContextFrame_CaptureTab_rawBuf0.inheritSelector = False
            self.CContextFrame_CaptureTab_rawBuf0.selector = ""
            self.CStaticPlot_Capture_rawBuf0.clear_items()
            self.CURVE_pydm_channel_capture_rawbuffer_0_timestamps = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_timestamps, color=QColor("#F0E912"))
            self.CURVE_pydm_channel_capture_rawbuffer_0 = self.CStaticPlot_Capture_rawBuf0.addCurve(data_source = self.pydm_channel_capture_rawbuffer_0, color=QColor("#FFFFFF"))
            self.CStaticPlot_Capture_rawBuf0.setDownsampling(auto=True, mode="peak")
            self.CStaticPlot_Capture_rawBuf0.plotItem.setClipToView(True)
            self.pydm_channel_capture_rawbuffer_0.context_changed()
            self.pydm_channel_capture_rawbuffer_0_timestamps.context_changed()

            # set channels for Capture tab rawBuffer1
            self.CContextFrame_CaptureTab_rawBuf1.inheritSelector = False
            self.CContextFrame_CaptureTab_rawBuf1.selector = ""
            self.CStaticPlot_Capture_rawBuf1.clear_items()
            self.CURVE_pydm_channel_capture_rawbuffer_1_timestamps = self.CStaticPlot_Capture_rawBuf1.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_timestamps, color=QColor("#F0E912"))
            self.CURVE_pydm_channel_capture_rawbuffer_1 = self.CStaticPlot_Capture_rawBuf1.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1, color=QColor("#FFFFFF"))
            self.CStaticPlot_Capture_rawBuf1.setDownsampling(auto=True, mode="peak")
            self.CStaticPlot_Capture_rawBuf1.plotItem.setClipToView(True)
            self.pydm_channel_capture_rawbuffer_1.context_changed()
            self.pydm_channel_capture_rawbuffer_1_timestamps.context_changed()

            # set channels for Capture tab rawBuffer0_FFT
            self.CContextFrame_CaptureTab_rawBuf0_FFT.inheritSelector = False
            self.CContextFrame_CaptureTab_rawBuf0_FFT.selector = ""
            self.CStaticPlot_Capture_rawBuf0_FFT.clear_items()
            self.CURVE_pydm_channel_capture_rawbuffer_0_FFT = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT, color=QColor("#FFFFFF"))
            self.CURVE_pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones = self.CStaticPlot_Capture_rawBuf0_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones, color=QColor('yellow'), line_style=Qt.NoPen, symbol="o", symbol_size=8)
            self.CStaticPlot_Capture_rawBuf0_FFT.setDownsampling(auto=True, mode="peak")
            # self.CStaticPlot_Capture_rawBuf0_FFT.plotItem.setClipToView(True)
            self.pydm_channel_capture_rawbuffer_0_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_0_FFT_xplots_overtones.context_changed()

            # set channels for Capture tab rawBuffer1_FFT
            self.CContextFrame_CaptureTab_rawBuf1_FFT.inheritSelector = False
            self.CContextFrame_CaptureTab_rawBuf1_FFT.selector = ""
            self.CStaticPlot_Capture_rawBuf1_FFT.clear_items()
            self.CURVE_pydm_channel_capture_rawbuffer_1_FFT = self.CStaticPlot_Capture_rawBuf1_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_FFT, color=QColor("#FFFFFF"))
            self.CURVE_pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones = self.CStaticPlot_Capture_rawBuf1_FFT.addCurve(data_source=self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones, color=QColor('yellow'), line_style=Qt.NoPen, symbol="o", symbol_size=8)
            self.CStaticPlot_Capture_rawBuf1_FFT.setDownsampling(auto=True, mode="peak")
            # self.CStaticPlot_Capture_rawBuf1_FFT.plotItem.setClipToView(True)
            self.pydm_channel_capture_rawbuffer_1_FFT.context_changed()
            self.pydm_channel_capture_rawbuffer_1_FFT_xplots_overtones.context_changed()

            # set channels for CLabel overtones of rawbuf0
            self.CContextFrame_CaptureTab_Overtones_FFT0.inheritSelector = False
            self.CContextFrame_CaptureTab_Overtones_FFT0.selector = ""
            self.CLabel_Overtones0_1.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_2.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_3.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_4.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_5.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_6.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"
            self.CLabel_Overtones0_7.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq0"

            # set channels for CLabel overtones of rawbuf1
            self.CContextFrame_CaptureTab_Overtones_FFT1.inheritSelector = False
            self.CContextFrame_CaptureTab_Overtones_FFT1.selector = ""
            self.CLabel_Overtones1_1.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_2.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_3.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_4.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_5.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_6.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"
            self.CLabel_Overtones1_7.channel = "UCAP.VD." + self.current_device + "/" + "bufferFFT#peaks_freq1"

        return

    #----------------------------------------------#

########################################################
########################################################