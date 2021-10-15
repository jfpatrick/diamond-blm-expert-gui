########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CContextFrame, CApplication, CLineEdit, CLabel, CCommandButton, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont)
from PyQt5.QtCore import (QSize, Qt, QRect)
from PyQt5.QtWidgets import (QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QMessageBox, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import json

########################################################
########################################################

# GLOBALS

UI_FILENAME = "settings_dialog_auto.ui"
SHOW_COMMANDS_IN_SETTINGS = False

########################################################
########################################################

class DialogThreeColumnSet(QDialog):

    #----------------------------------------------#

    def __init__(self, parent = None):

        # save the parent
        self.dialog_parent = parent

        # inherit from QDialog
        QDialog.__init__(self, parent)

        # retrieve the attributes
        self.pyccda_dictionary = parent.pyccda_dictionary
        self.app = parent.app
        self.property_list = parent.property_list
        self.current_device = parent.current_device
        self.current_accelerator = parent.current_accelerator
        self.current_selector = parent.current_selector
        self.field_dict = parent.field_dict
        self.japc = parent.japc
        self.field_values_macro_dict = parent.field_values_macro_dict

        # when you want to destroy the dialog set this to True
        self._want_to_close = False

        # set the window title and build the GUI
        self.setWindowTitle("DIAMOND BLM SETTINGS")
        self.buildCodeWidgets()
        self.bindWidgets()

        return

    #----------------------------------------------#

    # event for closing the window in a right way
    def closeEvent(self, evnt):

        # close event
        if self._want_to_close:
            super(DialogThreeColumnSet, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setVisible(False)

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # initialize widget dicts
        self.groupBoxDict = {}
        self.layoutDict = {}
        self.labelDict = {}
        self.lineEditDict = {}
        self.commandButtonDict = {}

        # resize the dialog window
        self.resize(1000, 800)

        # vertical layout of the main form of the dialog
        self.vertical_layout_main_dialog = QVBoxLayout(self)
        self.vertical_layout_main_dialog.setObjectName("vertical_layout_main_dialog")
        self.vertical_layout_main_dialog.setContentsMargins(6, 20, 6, 6)
        self.vertical_layout_main_dialog.setSpacing(2)

        # create the main frame
        self.frame_properties = QFrame(self)
        self.frame_properties.setObjectName("frame_properties")
        self.frame_properties.setFrameShape(QFrame.NoFrame)
        self.frame_properties.setFrameShadow(QFrame.Raised)

        # vertical layout of the frame
        self.vertical_layout_main_frame = QVBoxLayout(self.frame_properties)
        self.vertical_layout_main_frame.setObjectName("vertical_layout_main_frame")

        # scrolling area
        self.scrollArea_properties = QScrollArea(self.frame_properties)
        self.scrollArea_properties.setObjectName("scrollArea_properties")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_properties.sizePolicy().hasHeightForWidth())
        self.scrollArea_properties.setSizePolicy(sizePolicy)
        self.scrollArea_properties.setFrameShadow(QFrame.Plain)
        self.scrollArea_properties.setLineWidth(1)
        self.scrollArea_properties.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_properties.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_properties.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.scrollArea_properties.setWidgetResizable(True)
        self.scrollArea_properties.setAlignment(Qt.AlignCenter)

        # scrolling contents
        self.scrollingContents_properties = QWidget()
        self.scrollingContents_properties.setObjectName("scrollingContents_properties")
        self.scrollingContents_properties.setGeometry(QRect(0, 340, 594, 75))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollingContents_properties.sizePolicy().hasHeightForWidth())
        self.scrollingContents_properties.setSizePolicy(sizePolicy)

        # vertical layout fro the scrollingContents_properties
        self.verticalLayout_scrollingContents_properties = QVBoxLayout(self.scrollingContents_properties)
        self.verticalLayout_scrollingContents_properties.setObjectName("verticalLayout_scrollingContents_properties")

        # link the scrollingContents_properties with the scrollArea_properties and add the layouts
        self.scrollArea_properties.setWidget(self.scrollingContents_properties)
        self.vertical_layout_main_frame.addWidget(self.scrollArea_properties)
        self.vertical_layout_main_dialog.addWidget(self.frame_properties)

        # create the get set frame (even though it will only be a set button)
        self.frame_get_set = QFrame(self)
        self.frame_get_set.setObjectName("frame_get_set")
        self.frame_get_set.setFrameShape(QFrame.NoFrame)
        self.frame_get_set.setFrameShadow(QFrame.Plain)

        # layout for the frame_get_set
        self.horizontalLayout_frame_get_set = QHBoxLayout(self.frame_get_set)
        self.horizontalLayout_frame_get_set.setObjectName("horizontalLayout_frame_get_set")
        self.horizontalLayout_frame_get_set.setContentsMargins(9, 0, 9, -1)
        self.horizontalLayout_frame_get_set.setSpacing(16)

        # invisible scrollArea
        self.scrollArea_get_set = QScrollArea(self.frame_get_set)
        self.scrollArea_get_set.setObjectName("scrollArea_get_set")
        self.scrollArea_get_set.setStyleSheet("background-color: transparent;")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_get_set.sizePolicy().hasHeightForWidth())
        self.scrollArea_get_set.setSizePolicy(sizePolicy)
        self.scrollArea_get_set.setFrameShape(QFrame.NoFrame)
        self.scrollArea_get_set.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea_get_set.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_get_set.setWidgetResizable(True)
        self.scrollArea_get_set.setAlignment(Qt.AlignCenter)

        # make the scroll bar of the get and set panel invisible
        sp_scroll_area_get_set = self.scrollArea_get_set.verticalScrollBar().sizePolicy()
        sp_scroll_area_get_set.setRetainSizeWhenHidden(True)
        self.scrollArea_get_set.verticalScrollBar().setSizePolicy(sp_scroll_area_get_set)
        self.scrollArea_get_set.verticalScrollBar().hide()

        # invisible scrollingContents
        self.scrollingContents_get_set = QWidget()
        self.scrollingContents_get_set.setObjectName("scrollingContents_get_set")
        self.scrollingContents_get_set.setGeometry(QRect(0, 0, 1276, 68))

        # layout for scrollingContents_get_set
        self.horizontalLayout_scrollingContents_get_set = QHBoxLayout(self.scrollingContents_get_set)
        self.horizontalLayout_scrollingContents_get_set.setObjectName("horizontalLayout_scrollingContents_get_set")

        # add a spacer
        spacerItem_1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_scrollingContents_get_set.addItem(spacerItem_1)

        # font for pushbutton
        font_for_pushbutton = QFont()
        font_for_pushbutton.setBold(True)
        font_for_pushbutton.setWeight(75)

        # create set pushbutton
        self.pushButton_set = QPushButton(self.scrollingContents_get_set)
        self.pushButton_set.setObjectName("pushButton_set")
        self.pushButton_set.setMinimumSize(QSize(100, 32))
        self.pushButton_set.setFont(font_for_pushbutton)
        self.pushButton_set.setText("SET")

        # add it to the layout
        self.horizontalLayout_scrollingContents_get_set.addWidget(self.pushButton_set)

        # add another spacer
        spacerItem_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_scrollingContents_get_set.addItem(spacerItem_2)

        # link the rest of items
        self.scrollArea_get_set.setWidget(self.scrollingContents_get_set)
        self.horizontalLayout_frame_get_set.addWidget(self.scrollArea_get_set)

        # add everything to the vertical layout of the main form
        self.vertical_layout_main_dialog.addWidget(self.frame_get_set)
        self.vertical_layout_main_dialog.setStretch(0, 95)
        self.vertical_layout_main_dialog.setStretch(1, 5)

        # read and apply the qss files
        with open("../qss/scrollArea_properties.qss", "r") as fh:
            self.scrollArea_properties.setStyleSheet(fh.read())
        with open("../qss/scrollingContents_properties.qss", "r") as fh:
            self.scrollingContents_properties.setStyleSheet(fh.read())
        with open("../qss/pushButton_set.qss", "r") as fh:
            self.pushButton_set.setStyleSheet(fh.read())

        # set groupbox for the titles of the labels
        self.groupBox_for_titles = QGroupBox(self.scrollingContents_properties)
        self.groupBox_for_titles.setObjectName("groupBox_for_titles")
        self.groupBox_for_titles.setAlignment(Qt.AlignCenter)
        self.groupBox_for_titles.setFlat(True)
        self.groupBox_for_titles.setCheckable(False)
        self.groupBox_for_titles.setTitle("")
        self.horizontal_layout_groupBox_for_titles = QHBoxLayout(self.groupBox_for_titles)
        self.horizontal_layout_groupBox_for_titles.setObjectName("horizontal_layout_groupBox_for_titles")

        # set titles
        self.label_1 = QLabel(self.groupBox_for_titles)
        self.label_1.setObjectName("label_1")
        self.label_1.setProperty("type", 2)
        self.label_1.setAlignment(Qt.AlignCenter)
        self.label_1.setText("{}".format("Name"))
        self.label_1.setMinimumSize(QSize(120, 24))
        self.horizontal_layout_groupBox_for_titles.addWidget(self.label_1)
        self.label_2 = QLabel(self.groupBox_for_titles)
        self.label_2.setObjectName("label_2")
        self.label_2.setProperty("type", 2)
        self.label_2.setAlignment(Qt.AlignCenter)
        self.label_2.setAlignment(Qt.AlignCenter)
        self.label_2.setText("{}".format("Current value"))
        self.label_2.setMinimumSize(QSize(120, 24))
        self.horizontal_layout_groupBox_for_titles.addWidget(self.label_2)
        self.label_3 = QLabel(self.groupBox_for_titles)
        self.label_3.setObjectName("label_3")
        self.label_3.setProperty("type", 2)
        self.label_3.setAlignment(Qt.AlignCenter)
        self.label_3.setAlignment(Qt.AlignCenter)
        self.label_3.setText("{}".format("New value"))
        self.label_3.setMinimumSize(QSize(120, 24))
        self.horizontal_layout_groupBox_for_titles.addWidget(self.label_3)
        self.verticalLayout_scrollingContents_properties.addWidget(self.groupBox_for_titles)

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # create the group boxes
        for property in self.property_list:

            # property groupbox
            self.groupBoxDict["{}".format(property)] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format(property)].setObjectName("groupBox_{}".format(property))
            self.groupBoxDict["{}".format(property)].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format(property)].setFlat(True)
            self.groupBoxDict["{}".format(property)].setCheckable(False)
            self.groupBoxDict["{}".format(property)].setTitle("{}".format(property))
            self.groupBoxDict["{}".format(property)].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format(property)])

            # property layout
            self.layoutDict["groupBox_{}".format(property)] = QGridLayout(self.groupBoxDict["{}".format(property)])
            self.layoutDict["groupBox_{}".format(property)].setObjectName("layout_groupBox_{}".format(property))

            # add labels and lineedits to the layout of the property groupbox
            row = 0
            for field in self.field_dict["{}".format(property)]:

                # set label name (column == 0)
                column = 0
                self.labelDict["label_name_{}_{}".format(property, field)] = QLabel(self.groupBoxDict["{}".format(property)])
                self.labelDict["label_name_{}_{}".format(property, field)].setObjectName("label_name_{}_{}".format(property, field))
                self.labelDict["label_name_{}_{}".format(property, field)].setProperty("type", 1)
                self.labelDict["label_name_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                self.labelDict["label_name_{}_{}".format(property, field)].setText("{}".format(field))
                self.labelDict["label_name_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.labelDict["label_name_{}_{}".format(property, field)], row, column, 1, 1)

                # set label old value (column == 1)
                column = 1
                self.labelDict["label_old_value_{}_{}".format(property, field)] = QLabel(self.groupBoxDict["{}".format(property)])
                self.labelDict["label_old_value_{}_{}".format(property, field)].setObjectName("label_old_value_{}_{}".format(property, field))
                self.labelDict["label_old_value_{}_{}".format(property, field)].setProperty("type", 1)
                self.labelDict["label_old_value_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                self.labelDict["label_old_value_{}_{}".format(property, field)].setText("{}".format(self.field_values_macro_dict["{}".format(property)][field]))
                self.labelDict["label_old_value_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.labelDict["label_old_value_{}_{}".format(property, field)], row, column, 1, 1)

                # set lineedit (column == 2)
                column = 2
                self.lineEditDict["{}_{}".format(property, field)] = QLineEdit(self.groupBoxDict["{}".format(property)])
                self.lineEditDict["{}_{}".format(property, field)].setObjectName("lineEdit_{}_{}".format(property, field))
                sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(self.lineEditDict["{}_{}".format(property, field)].sizePolicy().hasHeightForWidth())
                self.lineEditDict["{}_{}".format(property, field)].setSizePolicy(sizePolicy)
                self.lineEditDict["{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                self.lineEditDict["{}_{}".format(property, field)].setText("{}".format(self.field_values_macro_dict["{}".format(property)][field]))
                self.lineEditDict["{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.lineEditDict["{}_{}".format(property, field)], row, column, 1, 1)

                # get the next field
                row += 1

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2.5)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

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

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET#2 pressed".format(UI_FILENAME))

        # init lists
        list_areAllFieldsJustTheSame = []
        list_dict_to_inject = []
        list_needs_warning_message_box = []
        list_mux = []

        # iterate over all properties
        for property in self.property_list:

            # create dictionary to inject
            dict_to_inject = {}

            # init the boolean
            areAllFieldsJustTheSame = True

            # iterate over all fields
            for field in self.field_dict["{}".format(property)]:

                # compare old and new values
                old_value = self.field_values_macro_dict["{}".format(property)]["{}".format(field)]
                new_value = self.lineEditDict["{}_{}".format(property, field)].text()

                # if at least one field is different, do a SET of the whole dictionary
                if str(old_value) != str(new_value):
                    areAllFieldsJustTheSame = False

                # inject the value
                dict_to_inject["{}".format(field)] = new_value

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # append the values
            if is_multiplexed == "True" and areAllFieldsJustTheSame == False:
                list_needs_warning_message_box.append(True)
            else:
                list_needs_warning_message_box.append(False)
            list_areAllFieldsJustTheSame.append(areAllFieldsJustTheSame)
            list_dict_to_inject.append(dict_to_inject)
            list_mux.append(is_multiplexed)

        # determine if there were changes that require a non-generic selector
        muxAndNotEmpty = any(list_needs_warning_message_box)

        # if the current selector is generic and there were changes on a non-mux channel, force the user to use a non-generic selector
        if muxAndNotEmpty and self.current_selector.split(".")[-1] == "ALL":

            # show warning message
            message_title = "WARNING"
            message_text = "You are trying to do a SET on a multiplexed property with the generic {} selector. Please select a specific USER if you wish to modify this field.".format(self.current_selector)
            self.message_box = QMessageBox.warning(self, message_title, message_text)

            # break the set action
            return

        # otherwise continue as normal
        else:

            # iterate over all properties
            for count_prop, property in enumerate(self.property_list):

                # if no changes
                if list_areAllFieldsJustTheSame[count_prop]:

                    # just continue
                    continue

                # if there were changes
                else:

                    # set the param
                    if list_mux[count_prop] == "True":
                        self.japc.setParam("{}/{}".format(self.current_device, property), list_dict_to_inject[count_prop], timingSelectorOverride = self.current_selector)
                    else:
                        self.japc.setParam("{}/{}".format(self.current_device, property), list_dict_to_inject[count_prop], timingSelectorOverride = "")

        # update values in the parent panel
        self.dialog_parent.getFunction()

        # close the dialog
        sleep(0.1)
        self._want_to_close = True
        self.close()
        self.deleteLater()

        return

    #----------------------------------------------#

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

        # set the device
        self.current_device = "dBLM.TEST4"
        self.current_accelerator = "LHC"
        self.LoadDeviceFromTxtPremain()

        # set current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # get the property list
        self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"].keys())

        # order the property list
        self.property_list.sort()

        # input the command list
        self.command_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["command"].keys())

        # order the command list
        self.command_list.sort()

        # initialize the field dictionary
        self.field_dict = {}

        # create japc object
        self.japc = pyjapc.PyJapc()

        # set japc selector
        self.japc.setSelector(self.current_selector)

        # load the gui, build the widgets and handle the signals
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("DIAMOND BLM SETTINGS")
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # init GET
        self.getFunction()

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # initialize widget dicts
        self.groupBoxDict = {}
        self.layoutDict = {}
        self.labelDict = {}
        self.clabelDict = {}
        self.lineEditDict = {}
        self.commandButtonDict = {}
        self.contextFrameDict = {}

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # only show the commands when needed
        if SHOW_COMMANDS_IN_SETTINGS:

            # set up the command groupbox first
            self.groupBoxDict["{}".format("Commands")] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format("Commands")].setObjectName("groupBox_{}".format("Commands"))
            self.groupBoxDict["{}".format("Commands")].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format("Commands")].setFlat(True)
            self.groupBoxDict["{}".format("Commands")].setCheckable(False)
            self.groupBoxDict["{}".format("Commands")].setTitle("{}".format("Commands"))
            self.groupBoxDict["{}".format("Commands")].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format("Commands")])

            # layout for the commands
            self.layoutDict["groupBox_{}".format("Commands")] = QGridLayout(self.groupBoxDict["{}".format("Commands")])
            self.layoutDict["groupBox_{}".format("Commands")].setObjectName("layout_groupBox_{}".format("Commands"))

            # add labels and ccommandbuttons to the layout of the command groupbox
            row = 0
            for command in self.command_list:

                # set label (column == 0)
                column = 0
                self.labelDict["{}_{}".format("Commands", command)] = QLabel(self.groupBoxDict["{}".format("Commands")])
                self.labelDict["{}_{}".format("Commands", command)].setObjectName("label_{}_{}".format("Commands", command))
                self.labelDict["{}_{}".format("Commands", command)].setAlignment(Qt.AlignCenter)
                self.labelDict["{}_{}".format("Commands", command)].setText("{}".format(command))
                self.labelDict["{}_{}".format("Commands", command)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format("Commands")].addWidget(self.labelDict["{}_{}".format("Commands", command)], row, column, 1, 1)

                # set ccommandbutton (column == 1)
                column = 1
                self.commandButtonDict["{}_{}".format("Commands", command)] = CCommandButton(self.groupBoxDict["{}".format("Commands")])
                self.commandButtonDict["{}_{}".format("Commands", command)].setObjectName("commandButton_{}_{}".format("Commands", command))
                sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(self.commandButtonDict["{}_{}".format("Commands", command)].sizePolicy().hasHeightForWidth())
                self.commandButtonDict["{}_{}".format("Commands", command)].setSizePolicy(sizePolicy)
                self.commandButtonDict["{}_{}".format("Commands", command)].setText("{}".format(" Run"))
                self.commandButtonDict["{}_{}".format("Commands", command)].setIcon(QIcon("../icons/command.png"))
                self.commandButtonDict["{}_{}".format("Commands", command)].channel = "{}/{}".format(self.current_device, command)
                self.commandButtonDict["{}_{}".format("Commands", command)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format("Commands")].addWidget(self.commandButtonDict["{}_{}".format("Commands", command)], row, column, 1, 1)

                # get the next field
                row += 1

        # create the group boxes
        for property in self.property_list:

            # property groupbox
            self.groupBoxDict["{}".format(property)] = QGroupBox(self.scrollingContents_properties)
            self.groupBoxDict["{}".format(property)].setObjectName("groupBox_{}".format(property))
            self.groupBoxDict["{}".format(property)].setAlignment(Qt.AlignCenter)
            self.groupBoxDict["{}".format(property)].setFlat(True)
            self.groupBoxDict["{}".format(property)].setCheckable(False)
            self.groupBoxDict["{}".format(property)].setTitle("{}".format(property))
            self.groupBoxDict["{}".format(property)].setFont(font_for_groupbox)
            self.verticalLayout_scrollingContents_properties.addWidget(self.groupBoxDict["{}".format(property)])

            # context frame of the groupbox
            self.contextFrameDict["CContextFrame_{}".format(property)] = CContextFrame(self.groupBoxDict["{}".format(property)])
            self.contextFrameDict["CContextFrame_{}".format(property)].setObjectName("CContextFrame_{}".format(property))
            self.contextFrameDict["CContextFrame_{}".format(property)].inheritSelector = False
            self.contextFrameDict["CContextFrame_{}".format(property)].selector = self.current_selector

            # layout of the context frame (0 margin)
            self.layoutDict["CContextFrame_{}".format(property)] = QVBoxLayout(self.groupBoxDict["{}".format(property)])
            self.layoutDict["CContextFrame_{}".format(property)].setObjectName("CContextFrame_{}".format(property))
            self.layoutDict["CContextFrame_{}".format(property)].setContentsMargins(0, 0, 0, 0)
            self.layoutDict["CContextFrame_{}".format(property)].addWidget(self.contextFrameDict["CContextFrame_{}".format(property)])

            # property layout
            self.layoutDict["groupBox_{}".format(property)] = QGridLayout(self.contextFrameDict["CContextFrame_{}".format(property)])
            self.layoutDict["groupBox_{}".format(property)].setObjectName("layout_groupBox_{}".format(property))

            # retrieve the field setting names
            self.field_dict["{}".format(property)] = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["scalar"].keys())
            self.field_dict["{}".format(property)].sort()

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # in case the property is multiplexed, create a subscription kind of channel (i.e. use CLabel)
            if is_multiplexed == "True":

                # add labels to the layout of the property groupbox
                row = 0
                for field in self.field_dict["{}".format(property)]:

                    # set label (column == 0)
                    column = 0
                    self.labelDict["label_name_{}_{}".format(property, field)] = QLabel(self.groupBoxDict["{}".format(property)])
                    self.labelDict["label_name_{}_{}".format(property, field)].setObjectName("label_name_{}_{}".format(property, field))
                    self.labelDict["label_name_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["label_name_{}_{}".format(property, field)].setText("{}".format(field))
                    self.labelDict["label_name_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                    self.layoutDict["groupBox_{}".format(property)].addWidget(self.labelDict["label_name_{}_{}".format(property, field)], row, column, 1, 1)

                    # set label (column == 1)
                    column = 1
                    self.clabelDict["clabel_value_{}_{}".format(property, field)] = CLabel(self.groupBoxDict["{}".format(property)])
                    self.clabelDict["clabel_value_{}_{}".format(property, field)].setObjectName("clabel_value_{}_{}".format(property, field))
                    self.clabelDict["clabel_value_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.clabelDict["clabel_value_{}_{}".format(property, field)].setText("{}".format("Null"))
                    self.clabelDict["clabel_value_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                    self.clabelDict["clabel_value_{}_{}".format(property, field)].channel = "{}/{}#{}".format(self.current_device, property, field)
                    self.layoutDict["groupBox_{}".format(property)].addWidget(self.clabelDict["clabel_value_{}_{}".format(property, field)], row, column, 1, 1)

                    # get the next field
                    row += 1

            # in case the property is not multiplexed, create a GET kind of channel (i.e. use QLabel)
            else:

                # add labels to the layout of the property groupbox
                row = 0
                for field in self.field_dict["{}".format(property)]:

                    # set label (column == 0)
                    column = 0
                    self.labelDict["label_name_{}_{}".format(property, field)] = QLabel(self.groupBoxDict["{}".format(property)])
                    self.labelDict["label_name_{}_{}".format(property, field)].setObjectName("label_name_{}_{}".format(property, field))
                    self.labelDict["label_name_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["label_name_{}_{}".format(property, field)].setText("{}".format(field))
                    self.labelDict["label_name_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                    self.layoutDict["groupBox_{}".format(property)].addWidget(self.labelDict["label_name_{}_{}".format(property, field)], row, column, 1, 1)

                    # set label (column == 1)
                    column = 1
                    self.labelDict["label_value_{}_{}".format(property, field)] = QLabel(self.groupBoxDict["{}".format(property)])
                    self.labelDict["label_value_{}_{}".format(property, field)].setObjectName("label_value_{}_{}".format(property, field))
                    self.labelDict["label_value_{}_{}".format(property, field)].setAlignment(Qt.AlignCenter)
                    self.labelDict["label_value_{}_{}".format(property, field)].setText("{}".format("Null"))
                    self.labelDict["label_value_{}_{}".format(property, field)].setMinimumSize(QSize(120, 24))
                    self.layoutDict["groupBox_{}".format(property)].addWidget(self.labelDict["label_value_{}_{}".format(property, field)], row, column, 1, 1)

                    # get the next field
                    row += 1

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2.5)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

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

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that retrieves and displays the values of the fields
    def getFunction(self):

        # print the GET action
        print("{} - Button GET pressed".format(UI_FILENAME))

        # create a field dictionary to see which fields changed
        self.field_values_macro_dict = {}

        # iterate over all properties
        for property in self.property_list:

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # in case the property is multiplexed, the connection is via subscription so a GET is useless (i.e. skip it)
            if is_multiplexed == "True":

                # get the field values from the label text
                self.field_values_macro_dict["{}".format(property)] = {}

                # iterate over all fields
                for field in self.field_dict["{}".format(property)]:

                    # fill the dict
                    self.field_values_macro_dict["{}".format(property)][field] = self.clabelDict["clabel_value_{}_{}".format(property, field)].text()

                # skip the property
                continue

            # in case the property is not multiplexed, a GET is required
            else:

                # get the new field values via pyjapc and add them to the field_values_macro_dict
                field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride="")

                # add field values to the macro dict
                self.field_values_macro_dict["{}".format(property)] = field_values

                # iterate over all fields
                for field in self.field_dict["{}".format(property)]:

                    # get and set the text into the label
                    self.labelDict["label_value_{}_{}".format(property, field)].setText("{}".format(field_values[field]))

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET#1 pressed".format(UI_FILENAME))

        # get before set
        self.getFunction()

        # open the dialog
        self.dialog_three_column_set = DialogThreeColumnSet(parent = self)
        self.dialog_three_column_set.show()

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

    # function that reads from the json file generated by the pyccda script
    def readPyCCDAJsonFile(self):

        # read pyccda info file
        if os.path.exists("aux_jsons/pyccda_sps.json"):
            with open("aux_jsons/pyccda_sps.json") as f:
                self.pyccda_dictionary = json.load(f)

        return

    #----------------------------------------------#

########################################################
########################################################