########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CValueAggregator, CDisplay, CApplication, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource, CContextFrame, CStaticPlot, CLabel, CCommandButton, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QBrush)
from PyQt5.QtCore import (QSize, Qt, QTimer)
from PyQt5.QtWidgets import (QSizePolicy, QWidget, QHBoxLayout, QHBoxLayout, QVBoxLayout, QSpacerItem, QFrame, QGridLayout, QLabel, QTabWidget)
import pyqtgraph as pg

# OTHER IMPORTS

import sys
import os
import numpy as np
from copy import deepcopy
import jpype as jp
import time
import json
import math
import numpy as np
from time import sleep

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

        # write boolean for fullscreens
        self.writeAuxFFTFileForFullscreen(is_fft_plotted = False)
        self.writeAuxBufferFileForFullscreen(is_buffer_plotted = False)

        # init aux booleans and variables
        self.data_aux_time = math.inf
        self.bufferFirstPlotsPainted = False
        self.bufferUcapFirstPlotsPainted = False
        self.compute_time_vector_first_time = True
        self.firstTimeUcap = False
        self.firstTimeCapture = False
        self.data_rawBuf0 = np.array([0])
        self.data_rawBuf1 = np.array([0])
        self.is_turn0_checked = True
        self.is_turn1_checked = True
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
        self.firstPlotPaintedDict = {}
        self.data_generic_dict = {}

        # retrieve the pyccda json info file
        self.readPyCCDAJsonFile()

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # import cern package for handling exceptions
        self.cern = jp.JPackage("cern")

        # set current device
        self.current_device = "SP.BA1.BLMDIAMOND.2"
        self.current_accelerator = "SPS"
        self.LoadDeviceFromTxtPremain()

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())
        self.pyccda_dictionary[self.current_accelerator][self.current_device]["cycle_bound"]

        # set current selector (check that the device is not the test device)
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # do not use a selector if the cycle bound is set to false
        if self.pyccda_dictionary[self.current_accelerator][self.current_device]["cycle_bound"] == "False":
            self.current_selector = ""

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

        # load and set the channels
        print("{} - Setting all channels...".format(UI_FILENAME))
        self.setChannels()

        # status bar message
        self.app.main_window.statusBar().showMessage("Device window loaded successfully!", 10*1000)
        self.app.main_window.statusBar().repaint()

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
        self.pyqtPlotDict = {}
        self.cvalueAggregatorDict = {}
        self.frameDict = {}

        # iterate over the property tabs
        for property in self.property_list:

            # init boolean to optimize generic plots
            self.firstPlotPaintedDict[property] = {}

            # init dict to store generic data
            self.data_generic_dict[property] = {}

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

                # aggregator for the property
                self.cvalueAggregatorDict["{}".format(property)] = CValueAggregator(self)
                self.cvalueAggregatorDict["{}".format(property)].setProperty("inputChannels", ['{}/{}'.format(self.current_device, property)])
                self.cvalueAggregatorDict["{}".format(property)].setObjectName("CValueAggregator_{}".format(property))
                self.cvalueAggregatorDict["{}".format(property)].setValueTransformation("try:\n"
                                                                     "    output(next(iter(values.values())))\n"
                                                                     "except:\n"
                                                                     "    output(0)")
                self.horizontalLayout_CValueAggregators.addWidget(self.cvalueAggregatorDict["{}".format(property)])

                # add the labels to the table
                row = 1
                for field in self.field_dict["{}".format(property)]["fields_that_are_not_arrays"]:

                    # init generic data fields
                    self.data_generic_dict[property][field] = "Null"

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
                self.clabelDict["{}_AcqTimestamp".format(property)].setText("<b>acqStamp:</b> Null UTC  ")
                self.data_generic_dict[property]["acqStamp"] = "Null"
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
                self.data_generic_dict[property]["cycleName"] = "Null"
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

                    # init boolean to optimize generic plots
                    self.firstPlotPaintedDict[property][field] = False

                    # init generic data plots
                    self.data_generic_dict[property][field] = np.array([0])

                    # get x and y labels for the plot
                    if "AcquisitionHistogram" == property:
                        y_label = "threshold crossings"
                        x_label = "bins"
                    elif "AcquisitionIntegral" == property:
                        y_label = "loss"
                        x_label = "bunch number"
                    elif "AcquisitionIntegralDist" == property:
                        y_label = "distribution"
                        x_label = "value"
                    elif "AcquisitionRawDist" == property:
                        y_label = "distribution"
                        x_label = "value"
                    elif "AcquisitionTurnLoss" == property:
                        y_label = "loss"
                        x_label = "turn number"
                    else:
                        y_label = "y"
                        x_label = "x"

                    # pyqt plot
                    self.pyqtPlotDict["{}_{}".format(property, field)] = pg.PlotWidget(title="{}".format(field))
                    self.pyqtPlotDict["{}_{}".format(property, field)].enableAutoRange()
                    self.pyqtPlotDict["{}_{}".format(property, field)].setAutoVisible()
                    self.pyqtPlotDict["{}_{}".format(property, field)].setMenuEnabled(enableMenu=False)
                    self.pyqtPlotDict["{}_{}".format(property, field)].showButtons()
                    self.pyqtPlotDict["{}_{}".format(property, field)].showGrid(x=True, y=True, alpha=0.4)
                    self.pyqtPlotDict["{}_{}".format(property, field)].getPlotItem().setLabel(axis='left', text=y_label)
                    self.pyqtPlotDict["{}_{}".format(property, field)].getPlotItem().setLabel(axis='bottom', text=x_label)
                    self.layoutDict["vertical_layout_tab_CStaticplot_area_{}".format(property)].addWidget(self.pyqtPlotDict["{}_{}".format(property, field)])

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

        #  get current tab and index
        self.current_tab_name = self.tab_names[tab_i]
        self.current_tab_index = tab_i

        # disable Capture buttons if CAPTURE_TAB is disabled
        # if CAPTURE_TAB and "dBLM.TEST" not in self.current_device:
        #     self.CRelatedDisplayButton_rawBuf0.setEnabled(True)
        #     self.CRelatedDisplayButton_rawBuf1.setEnabled(True)
        #     self.CRelatedDisplayButton_rawBuf0_FFT.setEnabled(True)
        #     self.CRelatedDisplayButton_rawBuf1_FFT.setEnabled(True)
        #     self.checkBox_turns_0.setEnabled(True)
        #     self.checkBox_turns_1.setEnabled(True)
        #     self.checkBox_peaks_0.setEnabled(True)
        #     self.checkBox_peaks_1.setEnabled(True)
        #     self.CLabel_acqStamp_Capture_0.setEnabled(True)
        #     self.CLabel_acqStamp_Capture_1.setEnabled(True)
        #     self.CLabel_cycleName_Capture_0.setEnabled(True)
        #     self.CLabel_cycleName_Capture_1.setEnabled(True)
        #     self.CLabel_Overtones0_1.setEnabled(True)
        #     self.CLabel_Overtones0_2.setEnabled(True)
        #     self.CLabel_Overtones0_3.setEnabled(True)
        #     self.CLabel_Overtones0_4.setEnabled(True)
        #     self.CLabel_Overtones0_5.setEnabled(True)
        #     self.CLabel_Overtones0_6.setEnabled(True)
        #     self.CLabel_Overtones0_7.setEnabled(True)
        #     self.CLabel_Overtones1_1.setEnabled(True)
        #     self.CLabel_Overtones1_2.setEnabled(True)
        #     self.CLabel_Overtones1_3.setEnabled(True)
        #     self.CLabel_Overtones1_4.setEnabled(True)
        #     self.CLabel_Overtones1_5.setEnabled(True)
        #     self.CLabel_Overtones1_6.setEnabled(True)
        #     self.CLabel_Overtones1_7.setEnabled(True)
        # else:
        #     self.CRelatedDisplayButton_rawBuf0.setEnabled(False)
        #     self.CRelatedDisplayButton_rawBuf1.setEnabled(False)
        #     self.CRelatedDisplayButton_rawBuf0_FFT.setEnabled(False)
        #     self.CRelatedDisplayButton_rawBuf1_FFT.setEnabled(False)
        #     self.checkBox_turns_0.setEnabled(False)
        #     self.checkBox_turns_1.setEnabled(False)
        #     self.checkBox_peaks_0.setEnabled(False)
        #     self.checkBox_peaks_1.setEnabled(False)
        #     self.CLabel_acqStamp_Capture_0.setEnabled(False)
        #     self.CLabel_acqStamp_Capture_1.setEnabled(False)
        #     self.CLabel_cycleName_Capture_0.setEnabled(False)
        #     self.CLabel_cycleName_Capture_1.setEnabled(False)
        #     self.CLabel_Overtones0_1.setEnabled(False)
        #     self.CLabel_Overtones0_2.setEnabled(False)
        #     self.CLabel_Overtones0_3.setEnabled(False)
        #     self.CLabel_Overtones0_4.setEnabled(False)
        #     self.CLabel_Overtones0_5.setEnabled(False)
        #     self.CLabel_Overtones0_6.setEnabled(False)
        #     self.CLabel_Overtones0_7.setEnabled(False)
        #     self.CLabel_Overtones1_1.setEnabled(False)
        #     self.CLabel_Overtones1_2.setEnabled(False)
        #     self.CLabel_Overtones1_3.setEnabled(False)
        #     self.CLabel_Overtones1_4.setEnabled(False)
        #     self.CLabel_Overtones1_5.setEnabled(False)
        #     self.CLabel_Overtones1_6.setEnabled(False)
        #     self.CLabel_Overtones1_7.setEnabled(False)

        # pyqtgraph plot for rabuf0
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0.removeItem(self.horizontalLayout_CaptureTab_rawBuf0)
        self.plot_rawbuf0 = pg.PlotWidget(title="rawBuf0")
        self.plot_rawbuf0.getPlotItem().enableAutoRange()
        self.plot_rawbuf0.getPlotItem().setAutoVisible()
        self.plot_rawbuf0.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0.getPlotItem().showButtons()
        self.plot_rawbuf0.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf0.getPlotItem().setClipToView(True)
        self.plot_rawbuf0.setDownsampling(auto=True, mode="peak")
        self.plot_rawbuf0.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf0.getPlotItem().setLabel(axis='bottom', text='time (microseconds)')
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0.addWidget(self.plot_rawbuf0)
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0.addItem(self.horizontalLayout_CaptureTab_rawBuf0)

        # pyqtgraph plot for rabuf1
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1.removeItem(self.horizontalLayout_CaptureTab_rawBuf1)
        self.plot_rawbuf1 = pg.PlotWidget(title="rawBuf1")
        self.plot_rawbuf1.getPlotItem().enableAutoRange()
        self.plot_rawbuf1.getPlotItem().setAutoVisible()
        self.plot_rawbuf1.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf1.getPlotItem().showButtons()
        self.plot_rawbuf1.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf1.getPlotItem().setClipToView(True)
        self.plot_rawbuf1.setDownsampling(auto=True, mode="peak")
        self.plot_rawbuf1.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf1.getPlotItem().setLabel(axis='bottom', text='time (microseconds)')
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1.addWidget(self.plot_rawbuf1)
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1.addItem(self.horizontalLayout_CaptureTab_rawBuf1)

        # pyqtgraph plot for rabuf0_fft
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0_FFT.removeItem(self.horizontalLayout_CaptureTab_rawBuf0_FFT)
        self.plot_rawbuf0_fft = pg.PlotWidget(title="rawBuf0_FFT")
        self.plot_rawbuf0_fft.getPlotItem().enableAutoRange()
        self.plot_rawbuf0_fft.getPlotItem().setAutoVisible()
        self.plot_rawbuf0_fft.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf0_fft.getPlotItem().showButtons()
        self.plot_rawbuf0_fft.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf0_fft.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf0_fft.getPlotItem().setLabel(axis='bottom', text='frequency (kHz)')
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0_FFT.addWidget(self.plot_rawbuf0_fft)
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf0_FFT.addItem(self.horizontalLayout_CaptureTab_rawBuf0_FFT)

        # pyqtgraph plot for rabuf1_fft
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1_FFT.removeItem(self.horizontalLayout_CaptureTab_rawBuf1_FFT)
        self.plot_rawbuf1_fft = pg.PlotWidget(title="rawBuf1_FFT")
        self.plot_rawbuf1_fft.getPlotItem().enableAutoRange()
        self.plot_rawbuf1_fft.getPlotItem().setAutoVisible()
        self.plot_rawbuf1_fft.getPlotItem().setMenuEnabled(enableMenu=False)
        self.plot_rawbuf1_fft.getPlotItem().showButtons()
        self.plot_rawbuf1_fft.getPlotItem().showGrid(x=True, y=True, alpha=0.4)
        self.plot_rawbuf1_fft.getPlotItem().setLabel(axis='left', text='amplitude')
        self.plot_rawbuf1_fft.getPlotItem().setLabel(axis='bottom', text='frequency (kHz)')
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1_FFT.addWidget(self.plot_rawbuf1_fft)
        self.verticalLayout_CContextFrame_CaptureTab_rawBuf1_FFT.addItem(self.horizontalLayout_CaptureTab_rawBuf1_FFT)

        # aggregator for Capture
        self.CValueAggregator_Capture = CValueAggregator(self)
        self.CValueAggregator_Capture.setProperty("inputChannels", ['{}/Capture'.format(self.current_device)])
        self.CValueAggregator_Capture.setObjectName("CValueAggregator_Capture")
        self.CValueAggregator_Capture.setValueTransformation("try:\n"
                                                             "    output(next(iter(values.values())))\n"
                                                             "except:\n"
                                                             "    output(0)")
        self.horizontalLayout_CValueAggregators.addWidget(self.CValueAggregator_Capture)

        # aggregator for Capture FFT (UCAP)
        self.CValueAggregator_Capture_FFT = CValueAggregator(self)
        self.CValueAggregator_Capture_FFT.setProperty("inputChannels", ['UCAP.VD.{}/bufferFFT'.format(self.current_device)])
        self.CValueAggregator_Capture_FFT.setObjectName("CValueAggregator_Capture_FFT")
        self.CValueAggregator_Capture_FFT.setValueTransformation("try:\n"
                                                             "    output(next(iter(values.values())))\n"
                                                             "except:\n"
                                                             "    output(0)")
        self.horizontalLayout_CValueAggregators.addWidget(self.CValueAggregator_Capture_FFT)

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

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        # capture tab aggregator signals
        self.CValueAggregator_Capture.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCapture)
        self.CValueAggregator_Capture_FFT.updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromCaptureFFT)
        for property in self.property_list:
            if str(property) not in self.exception_list:
                self.cvalueAggregatorDict["{}".format(property)].updateTriggered['PyQt_PyObject'].connect(self.receiveDataFromGenericProperty)

        # singleshot qtimer for adding a delay to the timer_keep_calling_capture_function_until_stamps_are_the_same timer
        self.single_shot_timer = QTimer(self)

        # init qtimer for capture
        self.timer_keep_calling_capture_function_until_stamps_are_the_same = QTimer(self)
        self.timer_keep_calling_capture_function_until_stamps_are_the_same.setInterval(250)
        self.timer_keep_calling_capture_function_until_stamps_are_the_same.timeout.connect(self.plotCaptureFunction)

        # set up a qtimer for the freezing events
        self.timer_for_freezing_events = QTimer(self)
        self.timer_for_freezing_events.setInterval(500)
        self.timer_for_freezing_events.timeout.connect(self.readFreezeFile)
        self.timer_for_freezing_events.start()

        # signal that gets activated when the current tab changes
        self.tabWidget.currentChanged.connect(self.tabChanged)

        return

    #----------------------------------------------#

    # function to update tab name and index
    def tabChanged(self, tab_index):

        # update tab name and index
        self.current_tab_name = self.tab_names[tab_index]
        self.current_tab_index = tab_index

        # update items when the tab changes (GENERIC PROPERTIES)
        if self.current_tab_name in self.data_generic_dict.keys():

            # check it is a generic property
            if str(self.current_tab_name) not in self.exception_list:

                # iterate over fields
                for field in self.field_dict["{}".format(self.current_tab_name)]["fields_that_are_not_arrays"]:

                    # check field exists
                    if field in self.data_generic_dict[self.current_tab_name].keys():

                        # update fields
                        self.clabelDict["{}_{}".format(self.current_tab_name, field)].setText("{}".format(self.data_generic_dict[self.current_tab_name][field]))

                # iterate over arrays
                for field in self.field_dict["{}".format(self.current_tab_name)]["fields_that_are_arrays"]:

                    # check field exists
                    if field in self.data_generic_dict[self.current_tab_name].keys():

                        # update plots
                        self.pyqtPlotDict["{}_{}".format(self.current_tab_name, field)].clear()
                        self.pyqtPlotDict["{}_{}".format(self.current_tab_name, field)].plot(self.data_generic_dict[self.current_tab_name][field], pen=(255, 255, 255), name="{}_{}".format(self.current_tab_name, field))
                        self.pyqtPlotDict["{}_{}".format(self.current_tab_name, field)].show()

                        # first plot boolean
                        self.firstPlotPaintedDict[self.current_tab_name][field] = True

                        # set up the acq timestamp and cyclename
                        self.clabelDict["{}_AcqTimestamp".format(self.current_tab_name)].setText("<b>acqStamp:</b> {} UTC  ".format(self.data_generic_dict[self.current_tab_name]["acqStamp"]))
                        self.clabelDict["{}_CycleName".format(self.current_tab_name)].setText("<b>cycleName:</b> {}".format(self.data_generic_dict[self.current_tab_name]["cycleName"]))

        # update items when tab changes (CAPTURE TAB)
        elif self.current_tab_name == "Capture":

            # plot the data
            self.plotCaptureFunction()

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromGenericProperty(self, data, verbose = False):

        # iterate over properties
        for property in self.property_list:

            # check it is a generic property
            if str(property) not in self.exception_list:

                # check data was received
                if set(list(self.field_dict["{}".format(property)]['fields_that_are_not_arrays'])).issubset(set(list(data.keys()))):

                    # print
                    if verbose:
                        print("{} - Data received for property {}...".format(UI_FILENAME, property))

                    # store cyclename and timestamp
                    self.data_generic_dict[property]["acqStamp"] = data["acqStamp"]
                    self.data_generic_dict[property]["cycleName"] = data["cycleName"]

                    # iterate over fields
                    for field in self.field_dict["{}".format(property)]["fields_that_are_not_arrays"]:

                        # store array
                        self.data_generic_dict[property][field] = data[field]

                        # freeze condition
                        if not self.freeze_everything:

                            # freeze in case we are not in the right tab
                            if self.current_tab_name == property:

                                # update fields
                                self.clabelDict["{}_{}".format(property, field)].setText("{}".format(self.data_generic_dict[property][field]))

                    # iterate over arrays
                    for field in self.field_dict["{}".format(property)]["fields_that_are_arrays"]:

                        # check that the values are different with respect to the previous iteration
                        if self.firstPlotPaintedDict[property][field]:
                            if np.array_equal(self.data_generic_dict[property][field], data[field]):
                                return

                        # store array
                        self.data_generic_dict[property][field] = data[field]

                        # freeze condition
                        if not self.freeze_everything:

                            # freeze in case we are not in the right tab
                            if self.current_tab_name == property:

                                # update plots
                                self.pyqtPlotDict["{}_{}".format(property, field)].clear()
                                self.pyqtPlotDict["{}_{}".format(property, field)].plot(self.data_generic_dict[property][field], pen=(255, 255, 255), name="{}_{}".format(property, field))
                                self.pyqtPlotDict["{}_{}".format(property, field)].show()

                                # first plot boolean
                                self.firstPlotPaintedDict[property][field] = True

                                # set up the acq timestamp and cyclename
                                self.clabelDict["{}_AcqTimestamp".format(property)].setText("<b>acqStamp:</b> {} UTC  ".format(self.data_generic_dict[property]["acqStamp"]))
                                self.clabelDict["{}_CycleName".format(property)].setText("<b>cycleName:</b> {}".format(self.data_generic_dict[property]["cycleName"]))

                    # stop iterating properties
                    break

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCapture(self, data, verbose = True):

        # if the arrays are empty just show a message and return
        if data['rawBuf0'].size == 0 or data['rawBuf1'].size == 0:
            self.app.main_window.statusBar().showMessage("CaptureTab - Buffers are empty..", 0)
            self.app.main_window.statusBar().repaint()
            return

        # first time init
        self.firstTimeCapture = True

        # print
        if verbose:
            print("{} - Received data from the Capture property!".format(UI_FILENAME))

        # get acqStamp and cycleName
        self.data_acqStamp = data['acqStamp']
        self.data_cycleName = data['cycleName']

        # print
        if verbose:
            print("{} - CAPTURE TIMESTAMP: {}".format(UI_FILENAME, self.data_acqStamp))

        # check that the arrays are different with respect to the previous iteration
        if self.bufferFirstPlotsPainted:
            if np.array_equal(self.data_rawBuf0, data['rawBuf0']) and np.array_equal(self.data_rawBuf1, data['rawBuf1']):
                return

        # store the rest of the data
        self.data_rawBuf0 = data['rawBuf0']
        self.data_rawBuf1= data['rawBuf1']
        self.data_rawBufFlags0 = data['rawBufFlags0']
        self.data_rawBufFlags1 = data['rawBufFlags1']

        # wait until data from UCAP is received AND stamps are the same
        if self.timer_keep_calling_capture_function_until_stamps_are_the_same.isActive() == False:
            self.single_shot_timer.singleShot(5000, self.singleShot)

        return

    #----------------------------------------------#

    # delay function
    def singleShot(self):

        # start the timer after a delay
        self.timer_keep_calling_capture_function_until_stamps_are_the_same.start()

        return

    #----------------------------------------------#

    # connect function
    def plotCaptureFunction(self, verbose = True):

        # boolean to see if we should only plot the buffer (not the FFT)
        plotOnlyBuffer = False

        # status bar message
        if not self.firstTimeCapture:
            self.app.main_window.statusBar().showMessage("CaptureTab - Waiting for the device to send new data...", 0)
            self.app.main_window.statusBar().repaint()

        # freeze condition (and freeze in case we are not in the capture tab)
        if (not self.freeze_everything) and self.current_tab_name == "Capture":

            # check that we received data from both sources
            if self.firstTimeUcap and self.firstTimeCapture:

                # check that both stamps are the same
                if self.data_acqStamp == self.data_acqStamp_ucap:

                    # disable the timer
                    if self.timer_keep_calling_capture_function_until_stamps_are_the_same.isActive() == True:
                        self.timer_keep_calling_capture_function_until_stamps_are_the_same.stop()

                    # double check
                    if time.time() >= self.data_aux_time:

                        # check data is not the same
                        if self.bufferUcapFirstPlotsPainted:
                            if np.array_equal(self.current_data_rawBuffer0_FFT, self.data_rawBuffer0_FFT) and np.array_equal(self.current_data_rawBuffer1_FFT, self.data_rawBuffer1_FFT):
                                return
                        if self.bufferFirstPlotsPainted:
                            if np.array_equal(self.data_rawBuf0, self.current_data_rawBuf0) and np.array_equal(self.data_rawBuf1, self.current_data_rawBuf1):
                                return

                        # status bar message
                        self.app.main_window.statusBar().showMessage("CaptureTab - Received synced data from both UCAP and the device!", 0)
                        self.app.main_window.statusBar().repaint()

                        # print
                        if verbose:
                            print("{} - Timestamps are the same (SYNC IN ORDER)".format(UI_FILENAME))

                        # get the time vector in microseconds only one time
                        if self.compute_time_vector_first_time:
                            Fs = 0.65
                            self.time_vector = np.linspace(0, (len(self.data_rawBuf0) - 1) * (1 / (Fs * 1000)), num=len(self.data_rawBuf0))
                            self.compute_time_vector_first_time = False

                        # offset
                        offset_for_timestamps = 0

                        # line equation parameters
                        y_1 = np.min(self.data_rawBuf0) - offset_for_timestamps
                        y_2 = np.max(self.data_rawBuf0) + offset_for_timestamps
                        x_1 = 0
                        x_2 = 1

                        # for turn flags0
                        self.data_turn_line_eq_params_0 = [float(x_1), float(x_2), float(y_1), float(y_2)]

                        # line equation parameters
                        y_1 = np.min(self.data_rawBuf1) - offset_for_timestamps
                        y_2 = np.max(self.data_rawBuf1) + offset_for_timestamps
                        x_1 = 0
                        x_2 = 1

                        # for turn flags1
                        self.data_turn_line_eq_params_1 = [float(x_1), float(x_2), float(y_1), float(y_2)]

                        # get only turn flags (5 and 6) for buf0
                        idx_flags_five_six = np.where((self.data_rawBufFlags0 == 5) | (self.data_rawBufFlags0 == 6))[0]
                        flags_five_six = np.zeros(self.data_rawBufFlags0.shape)
                        flags_five_six[idx_flags_five_six] = 1

                        # re-scale the flags0 curve
                        self.flags_turn0 = ((self.data_turn_line_eq_params_0[3] - self.data_turn_line_eq_params_0[2]) /
                                            self.data_turn_line_eq_params_0[1]) * flags_five_six + self.data_turn_line_eq_params_0[2]

                        # get only turn flags (5 and 6) for buf1
                        idx_flags_five_six = np.where((self.data_rawBufFlags1 == 5) | (self.data_rawBufFlags1 == 6))[0]
                        flags_five_six = np.zeros(self.data_rawBufFlags1.shape)
                        flags_five_six[idx_flags_five_six] = 1

                        # re-scale the flags1 curve
                        self.flags_turn1 = ((self.data_turn_line_eq_params_1[3] - self.data_turn_line_eq_params_1[2]) /
                                            self.data_turn_line_eq_params_1[1]) * flags_five_six + self.data_turn_line_eq_params_1[2]

                        # plot the data for buf0
                        self.plot_rawbuf0.getPlotItem().clear()
                        self.plot_rawbuf0_fft.getPlotItem().clear()
                        if self.flags_turn0.size != 0 and self.is_turn0_checked:
                            self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                        self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                        if self.data_peaks_freq0_xplots.size != 0 and self.is_peaks0_checked:
                            self.plot_rawbuf0_fft.plot(x=self.data_peaks_freq0_xplots[1], y=self.data_peaks_freq0_xplots[0], pen=None, symbolBrush=(255,255,0), symbol='x', symbolPen=(255,255,0), symbolSize=8, name="rawBuf0_peaks")
                        self.plot_rawbuf0_fft.plot(x=self.data_rawBuffer0_FFT[1, :], y=self.data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
                        self.plot_rawbuf0.show()
                        self.plot_rawbuf0_fft.show()

                        # save current plotted data for checkbuttons
                        self.current_time_vector = self.time_vector
                        self.current_flags_turn0 = self.flags_turn0
                        self.current_data_rawBuf0 = self.data_rawBuf0
                        self.current_data_peaks_freq0_xplots = self.data_peaks_freq0_xplots
                        self.current_data_rawBuffer0_FFT = self.data_rawBuffer0_FFT
                        self.current_data_peaks_freq0 = self.data_peaks_freq0

                        # set the text fields of the frequency peaks
                        self.CLabel_Overtones0_1.setText("{0:.2f} kHz".format(self.data_peaks_freq0[0]))
                        self.CLabel_Overtones0_2.setText("{0:.2f} kHz".format(self.data_peaks_freq0[1]))
                        self.CLabel_Overtones0_3.setText("{0:.2f} kHz".format(self.data_peaks_freq0[2]))
                        self.CLabel_Overtones0_4.setText("{0:.2f} kHz".format(self.data_peaks_freq0[3]))
                        self.CLabel_Overtones0_5.setText("{0:.2f} kHz".format(self.data_peaks_freq0[4]))
                        self.CLabel_Overtones0_6.setText("{0:.2f} kHz".format(self.data_peaks_freq0[5]))
                        self.CLabel_Overtones0_7.setText("{0:.2f} kHz".format(self.data_peaks_freq0[6]))

                        # plot the data for buf1
                        self.plot_rawbuf1.getPlotItem().clear()
                        self.plot_rawbuf1_fft.getPlotItem().clear()
                        if self.flags_turn1.size != 0 and self.is_turn1_checked:
                            self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                        self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                        if self.data_peaks_freq1_xplots.size != 0 and self.is_peaks1_checked:
                            self.plot_rawbuf1_fft.plot(x=self.data_peaks_freq1_xplots[1], y=self.data_peaks_freq1_xplots[0], pen=None, symbolBrush=(255,255,0), symbol='x', symbolPen=(255,255,0), symbolSize=8, name="rawBuf1_peaks")
                        self.plot_rawbuf1_fft.plot(x=self.data_rawBuffer1_FFT[1, :], y=self.data_rawBuffer1_FFT[0, :], pen=(255, 255, 255), name="rawBuf1_FFT")
                        self.plot_rawbuf1.show()
                        self.plot_rawbuf1_fft.show()

                        # save current plotted data for checkbuttons
                        self.current_time_vector = self.time_vector
                        self.current_flags_turn1 = self.flags_turn1
                        self.current_data_rawBuf1 = self.data_rawBuf1
                        self.current_data_peaks_freq1_xplots = self.data_peaks_freq1_xplots
                        self.current_data_rawBuffer1_FFT = self.data_rawBuffer1_FFT
                        self.current_data_peaks_freq1 = self.data_peaks_freq1

                        # set the text fields of the frequency peaks
                        self.CLabel_Overtones1_1.setText("{0:.2f} kHz".format(self.data_peaks_freq1[0]))
                        self.CLabel_Overtones1_2.setText("{0:.2f} kHz".format(self.data_peaks_freq1[1]))
                        self.CLabel_Overtones1_3.setText("{0:.2f} kHz".format(self.data_peaks_freq1[2]))
                        self.CLabel_Overtones1_4.setText("{0:.2f} kHz".format(self.data_peaks_freq1[3]))
                        self.CLabel_Overtones1_5.setText("{0:.2f} kHz".format(self.data_peaks_freq1[4]))
                        self.CLabel_Overtones1_6.setText("{0:.2f} kHz".format(self.data_peaks_freq1[5]))
                        self.CLabel_Overtones1_7.setText("{0:.2f} kHz".format(self.data_peaks_freq1[6]))

                        # set cycle information
                        self.CLabel_acqStamp_Capture_0.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
                        self.CLabel_cycleName_Capture_0.setText("<b>cycleName:</b> {}".format(self.data_cycleName))
                        self.CLabel_acqStamp_Capture_1.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp_ucap))
                        self.CLabel_cycleName_Capture_1.setText("<b>cycleName:</b> {}".format(self.data_cycleName_ucap))

                        # update first plot boolean
                        self.bufferFirstPlotsPainted = True
                        self.bufferUcapFirstPlotsPainted = True

                        # write aux txt for the fullscreen plots
                        self.writeAuxFFTFileForFullscreen(is_fft_plotted = True)
                        self.writeAuxBufferFileForFullscreen(is_buffer_plotted = True)

                        # status bar message
                        self.app.main_window.statusBar().showMessage("CaptureTab - Buffer and FFT plotted succesfully!", 15*1000)
                        self.app.main_window.statusBar().repaint()

                # if stamps are different only plot the buffer
                else:

                    # update boolean
                    plotOnlyBuffer = True

            # if we only received the buffer only plot the buffer
            elif self.firstTimeCapture:

                # update boolean
                plotOnlyBuffer = True

            # plot only the buffer
            if plotOnlyBuffer:

                # status bar message
                self.app.main_window.statusBar().showMessage("CaptureTab - Waiting for UCAP to send new data...", 0)
                self.app.main_window.statusBar().repaint()

                # do not plot if data is just the same
                if self.bufferFirstPlotsPainted:
                    if np.array_equal(self.data_rawBuf0, self.current_data_rawBuf0) and np.array_equal(self.data_rawBuf1, self.current_data_rawBuf1):
                        return

                # disable the timer
                if self.timer_keep_calling_capture_function_until_stamps_are_the_same.isActive() == True:
                    self.timer_keep_calling_capture_function_until_stamps_are_the_same.stop()

                # get the time vector in microseconds only one time
                if self.compute_time_vector_first_time:
                    Fs = 0.65
                    self.time_vector = np.linspace(0, (len(self.data_rawBuf0) - 1) * (1 / (Fs * 1000)), num=len(self.data_rawBuf0))
                    self.compute_time_vector_first_time = False

                # offset
                offset_for_timestamps = 0

                # line equation parameters
                y_1 = np.min(self.data_rawBuf0) - offset_for_timestamps
                y_2 = np.max(self.data_rawBuf0) + offset_for_timestamps
                x_1 = 0
                x_2 = 1

                # for turn flags0
                self.data_turn_line_eq_params_0 = [float(x_1), float(x_2), float(y_1), float(y_2)]

                # line equation parameters
                y_1 = np.min(self.data_rawBuf1) - offset_for_timestamps
                y_2 = np.max(self.data_rawBuf1) + offset_for_timestamps
                x_1 = 0
                x_2 = 1

                # for turn flags1
                self.data_turn_line_eq_params_1 = [float(x_1), float(x_2), float(y_1), float(y_2)]

                # get only turn flags (5 and 6) for buf0
                idx_flags_five_six = np.where((self.data_rawBufFlags0 == 5) | (self.data_rawBufFlags0 == 6))[0]
                flags_five_six = np.zeros(self.data_rawBufFlags0.shape)
                flags_five_six[idx_flags_five_six] = 1

                # re-scale the flags0 curve
                self.flags_turn0 = ((self.data_turn_line_eq_params_0[3] - self.data_turn_line_eq_params_0[2]) /
                                    self.data_turn_line_eq_params_0[1]) * flags_five_six + self.data_turn_line_eq_params_0[2]

                # get only turn flags (5 and 6) for buf1
                idx_flags_five_six = np.where((self.data_rawBufFlags1 == 5) | (self.data_rawBufFlags1 == 6))[0]
                flags_five_six = np.zeros(self.data_rawBufFlags1.shape)
                flags_five_six[idx_flags_five_six] = 1

                # re-scale the flags1 curve
                self.flags_turn1 = ((self.data_turn_line_eq_params_1[3] - self.data_turn_line_eq_params_1[2]) /
                                    self.data_turn_line_eq_params_1[1]) * flags_five_six + self.data_turn_line_eq_params_1[2]

                # plot the data for buf0
                self.plot_rawbuf0.getPlotItem().clear()
                if self.flags_turn0.size != 0 and self.is_turn0_checked:
                    self.plot_rawbuf0.plot(x=self.time_vector, y=self.flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                self.plot_rawbuf0.plot(x=self.time_vector, y=self.data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

                # save current plotted data for checkbuttons
                self.current_time_vector = self.time_vector
                self.current_flags_turn0 = self.flags_turn0
                self.current_data_rawBuf0 = self.data_rawBuf0

                # plot the data for buf1
                self.plot_rawbuf1.getPlotItem().clear()
                if self.flags_turn1.size != 0 and self.is_turn1_checked:
                    self.plot_rawbuf1.plot(x=self.time_vector, y=self.flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                self.plot_rawbuf1.plot(x=self.time_vector, y=self.data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

                # save current plotted data for checkbuttons
                self.current_time_vector = self.time_vector
                self.current_flags_turn1 = self.flags_turn1
                self.current_data_rawBuf1 = self.data_rawBuf1

                # set cycle information
                self.CLabel_acqStamp_Capture_0.setText("<b>acqStamp:</b> {} UTC  ".format(self.data_acqStamp))
                self.CLabel_cycleName_Capture_0.setText("<b>cycleName:</b> {}".format(self.data_cycleName))

                # update first plot boolean
                self.bufferFirstPlotsPainted = True

                # write aux txt for the fullscreen plots
                self.writeAuxFFTFileForFullscreen(is_fft_plotted = False)
                self.writeAuxBufferFileForFullscreen(is_buffer_plotted = True)

        return

    #----------------------------------------------#

    # connect function
    def receiveDataFromCaptureFFT(self, data, verbose = True):

        # if the arrays are empty just show a message and return
        if data['rawBuffer0_FFT'].size == 0 or data['rawBuffer1_FFT'].size == 0:
            self.app.main_window.statusBar().showMessage("CaptureTab - Buffers are empty..", 0)
            self.app.main_window.statusBar().repaint()
            return

        # first time init
        self.firstTimeUcap = True

        # print
        if verbose:
            print("{} - Received data from the UCAP node!".format(UI_FILENAME))

        # store the data
        self.data_aux_time = data['aux_time']
        self.data_rawBuffer0_FFT = data['rawBuffer0_FFT']
        self.data_rawBuffer1_FFT = data['rawBuffer1_FFT']
        self.data_peaks_freq0 = data['peaks_freq0']
        self.data_peaks_freq1 = data['peaks_freq1']
        self.data_peaks_freq0_xplots = data['peaks_freq0_xplots']
        self.data_peaks_freq1_xplots = data['peaks_freq1_xplots']
        self.data_acqStamp_ucap = data['acqStamp']
        self.data_cycleName_ucap = data['cycleName']

        # print
        if verbose:
            print("{} - UCAP TIMESTAMP: {}".format(UI_FILENAME, self.data_acqStamp_ucap))

        # wait until data from UCAP is received AND stamps are the same
        if self.timer_keep_calling_capture_function_until_stamps_are_the_same.isActive() == False:
            self.single_shot_timer.singleShot(5000, self.singleShot)

        return

    #----------------------------------------------#

    # function that handles japc and UI stuff when rbac is disconnected
    def rbacLogoutSucceeded(self):

        # print message
        print("{} - RBAC logout succeeded...".format(UI_FILENAME))

        return

    #----------------------------------------------#

    # this function gets activated whenever RBAC logins successfully
    def rbacLoginSucceeded(self):

        # print message
        print("{} - RBAC login succeeded...".format(UI_FILENAME))

        # save the token into the environmental variable so that we can read it with pyjapc
        os.environ["RBAC_TOKEN_SERIALIZED"] = self.app._rbac.serialized_token

        return

    #----------------------------------------------#

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # do not use a selector if the cycle bound is set to false
        if self.pyccda_dictionary[self.current_accelerator][self.current_device]["cycle_bound"] == "False":
            self.current_selector = ""

        # print the selector
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

    # function that reads the freezing event txt
    def readFreezeFile(self):

        # check if we should freeze the plots
        if os.path.exists("aux_txts/freeze.txt"):
            self.freeze_everything = True
        else:
            self.freeze_everything = False

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf0
    def pleaseShowTurns0(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf0.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns0 button checked...".format(UI_FILENAME))
            self.current_check_dict["ts0"] = True
            self.is_turn0_checked = True
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                if self.current_flags_turn0.size != 0:
                    self.plot_rawbuf0.plot(x=self.current_time_vector, y=self.current_flags_turn0, pen=(255, 255, 0), name="rawBuf0_turn_flags")
                if self.current_check_dict["ts0"]:
                    self.plot_rawbuf0.plot(x=self.current_time_vector, y=self.current_data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        # if it is not checked
        else:

            # remove the flags
            print("{} - Turns0 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["ts0"] = False
            self.is_turn0_checked = False
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf0.getPlotItem().clear()
                self.plot_rawbuf0.plot(x=self.current_time_vector, y=self.current_data_rawBuf0, pen=(255, 255, 255), name="rawBuf0")
                self.plot_rawbuf0.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf0.getPlotItem().setClipToView(True)

        return

    #----------------------------------------------#

    # function to add or remove the turn flags from the plot of rawbuf1
    def pleaseShowTurns1(self, state):

        # reset clip to view to avoid errors
        self.plot_rawbuf1.getPlotItem().setClipToView(False)

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new flags
            print("{} - Turns1 button checked...".format(UI_FILENAME))
            self.current_check_dict["ts1"] = True
            self.is_turn1_checked = True
            self.plot_rawbuf1.getPlotItem().clear()
            if self.bufferFirstPlotsPainted:
                if self.current_flags_turn1.size != 0:
                    self.plot_rawbuf1.plot(x=self.current_time_vector, y=self.current_flags_turn1, pen=(255, 255, 0), name="rawBuf1_turn_flags")
                if self.current_check_dict["ts1"]:
                    self.plot_rawbuf1.plot(x=self.current_time_vector, y=self.current_data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

        # if it is not checked
        else:

            # remove the flags
            print("{} - Turns1 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["ts1"] = False
            self.is_turn1_checked = False
            if self.bufferFirstPlotsPainted:
                self.plot_rawbuf1.getPlotItem().clear()
                self.plot_rawbuf1.plot(x=self.current_time_vector, y=self.current_data_rawBuf1, pen=(255, 255, 255), name="rawBuf1")
                self.plot_rawbuf1.show()

        # reset clip to view to avoid errors
        self.plot_rawbuf1.getPlotItem().setClipToView(True)

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf0_FFT
    def pleaseShowPeaks0(self, state):

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new peaks
            print("{} - Peaks0 button checked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = True
            self.is_peaks0_checked = True
            if self.bufferUcapFirstPlotsPainted:
                self.plot_rawbuf0_fft.getPlotItem().clear()
                if self.current_data_peaks_freq0_xplots.size != 0:
                    self.plot_rawbuf0_fft.plot(x=self.current_data_peaks_freq0_xplots[1], y=self.current_data_peaks_freq0_xplots[0], pen=None, symbolBrush=(255, 255, 0), symbol='x', symbolPen=(255, 255, 0), symbolSize=8, name="rawBuf0_peaks")
                if self.current_check_dict["peaks0"]:
                    self.plot_rawbuf0_fft.plot(x=self.current_data_rawBuffer0_FFT[1, :], y=self.current_data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
                self.plot_rawbuf0_fft.show()

        # if it is not checked
        else:

            # remove the peaks
            print("{} - Peaks0 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["peaks0"] = False
            self.is_peaks0_checked = False
            if self.bufferUcapFirstPlotsPainted:
                self.plot_rawbuf0_fft.getPlotItem().clear()
                self.plot_rawbuf0_fft.plot(x=self.current_data_rawBuffer0_FFT[1, :], y=self.current_data_rawBuffer0_FFT[0, :], pen=(255, 255, 255), name="rawBuf0_FFT")
                self.plot_rawbuf0_fft.show()

        return

    #----------------------------------------------#

    # function to add or remove the peaks from the plot of rawbuf1_FFT
    def pleaseShowPeaks1(self, state):

        # if the button is checked
        if state == Qt.Checked:

            # clear plot and add the new peaks
            print("{} - Peaks1 button checked...".format(UI_FILENAME))
            self.current_check_dict["peaks1"] = True
            self.is_peaks1_checked = True
            if self.bufferUcapFirstPlotsPainted:
                self.plot_rawbuf1_fft.getPlotItem().clear()
                if self.current_data_peaks_freq1_xplots.size != 0:
                    self.plot_rawbuf1_fft.plot(x=self.current_data_peaks_freq1_xplots[1], y=self.current_data_peaks_freq1_xplots[0], pen=None, symbolBrush=(255, 255, 0), symbol='x', symbolPen=(255, 255, 0), symbolSize=8, name="rawBuf1_peaks")
                if self.current_check_dict["peaks1"]:
                    self.plot_rawbuf1_fft.plot(x=self.current_data_rawBuffer1_FFT[1, :], y=self.current_data_rawBuffer1_FFT[0, :], pen=(255, 255, 255), name="rawBuf1_FFT")
                self.plot_rawbuf1_fft.show()

        # if it is not checked
        else:

            # remove the peaks
            print("{} - Peaks1 button unchecked...".format(UI_FILENAME))
            self.current_check_dict["peaks1"] = False
            self.is_peaks1_checked = False
            if self.bufferUcapFirstPlotsPainted:
                self.plot_rawbuf1_fft.getPlotItem().clear()
                self.plot_rawbuf1_fft.plot(x=self.current_data_rawBuffer1_FFT[1, :], y=self.current_data_rawBuffer1_FFT[0, :], pen=(255, 255, 255), name="rawBuf1_FFT")
                self.plot_rawbuf1_fft.show()

        return

    #----------------------------------------------#

    # function that set the right channels for each widget depending on the selected device
    def setChannels(self):

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

        return

    #----------------------------------------------#

    # function to write aux fft file
    def writeAuxFFTFileForFullscreen(self, is_fft_plotted = False):

        # create the dir in case it does not exist
        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        # write file
        with open("aux_txts/is_fft_plotted.txt", "w") as f:
            if is_fft_plotted:
                f.write("True")
            else:
                f.write("False")

        return

    #----------------------------------------------#

    # function to write aux buffer file
    def writeAuxBufferFileForFullscreen(self, is_buffer_plotted = False):

        # create the dir in case it does not exist
        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        # write file
        with open("aux_txts/is_buffer_plotted.txt", "w") as f:
            if is_buffer_plotted:
                f.write("True")
            else:
                f.write("False")

        return

    #----------------------------------------------#

########################################################
########################################################