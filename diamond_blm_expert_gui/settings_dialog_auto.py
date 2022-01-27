########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CApplication, CContextFrame, CApplication, CLineEdit, CLabel, CCommandButton, CDisplay, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QFont, QBrush)
from PyQt5.QtCore import (QSize, Qt, QRect, QTimer, QAbstractTableModel)
from PyQt5.QtWidgets import (QTableView, QSizePolicy, QTableWidget, QAbstractItemView, QTableWidgetItem, QAbstractScrollArea, QHeaderView, QScrollArea, QSpacerItem, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDialog, QMessageBox, QFrame, QWidget)

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyjapc
import json
from general_utils import createCustomTempDir, getSystemTempDir

########################################################
########################################################

# GLOBALS

# ui file
UI_FILENAME = "settings_dialog_auto.ui"

# paths
TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"

# others
SHOW_COMMANDS_IN_SETTINGS = False

########################################################
########################################################

# util function
def can_be_converted_to_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

########################################################
########################################################

class TableModel(QAbstractTableModel):

    def __init__(self, data, header_labels, titles_set_window = False, three_column_window = False):

        super(TableModel, self).__init__()
        self._data = data
        self._header_labels = header_labels
        self.titles_set_window = titles_set_window
        self.three_column_window = three_column_window

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
            if self.three_column_window and col == 2:
                return QBrush(QColor("#ffffff"))

    def rowCount(self, index):

        return len(self._data)

    def columnCount(self, index):

        return len(self._data[0])

    def flags(self, index):

        if index.column() == 2:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):

        if role == Qt.EditRole and index.column() == 2:
            self._data[index.row()][index.column()] = value
            return True

        return False

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
        self.tableViewDict = {}
        self.dataTableModelDict = {}
        self.dataModelDict = {}

        # resize the dialog window
        self.resize(400, 800)

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
        with open("qss/scrollArea_properties.qss", "r") as fh:
            self.scrollArea_properties.setStyleSheet(fh.read())
        with open("qss/scrollingContents_properties.qss", "r") as fh:
            self.scrollingContents_properties.setStyleSheet(fh.read())
        with open("qss/pushButton_set.qss", "r") as fh:
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

        # set table titles
        self.tableViewDict["titles"] = QTableView(self.groupBox_for_titles)
        self.tableViewDict["titles"].setStyleSheet("QTableView{\n"
                                                   "    background-color: rgb(243, 243, 243);\n"
                                                   "    margin-top: 0;\n"
                                                   "}")
        self.tableViewDict["titles"].setFrameShape(QFrame.StyledPanel)
        self.tableViewDict["titles"].setFrameShadow(QFrame.Plain)
        self.tableViewDict["titles"].setDragEnabled(False)
        self.tableViewDict["titles"].setAlternatingRowColors(True)
        self.tableViewDict["titles"].setSelectionMode(QAbstractItemView.NoSelection)
        self.tableViewDict["titles"].setShowGrid(True)
        self.tableViewDict["titles"].setGridStyle(Qt.SolidLine)
        self.tableViewDict["titles"].setObjectName("tableView_general_information")
        self.tableViewDict["titles"].horizontalHeader().setVisible(False)
        self.tableViewDict["titles"].horizontalHeader().setHighlightSections(False)
        self.tableViewDict["titles"].verticalHeader().setDefaultSectionSize(0)
        self.tableViewDict["titles"].horizontalHeader().setMinimumSectionSize(0)
        self.tableViewDict["titles"].horizontalHeader().setStretchLastSection(True)
        self.tableViewDict["titles"].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.tableViewDict["titles"].verticalHeader().setVisible(False)
        self.tableViewDict["titles"].verticalHeader().setDefaultSectionSize(25)
        self.tableViewDict["titles"].verticalHeader().setHighlightSections(False)
        self.tableViewDict["titles"].verticalHeader().setMinimumSectionSize(25)
        self.tableViewDict["titles"].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableViewDict["titles"].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableViewDict["titles"].setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableViewDict["titles"].setFocusPolicy(Qt.NoFocus)
        self.tableViewDict["titles"].setSelectionMode(QAbstractItemView.NoSelection)
        self.tableViewDict["titles"].horizontalHeader().setFixedHeight(0)
        self.tableViewDict["titles"].horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
        self.tableViewDict["titles"].show()
        self.horizontal_layout_groupBox_for_titles.addWidget(self.tableViewDict["titles"])
        self.dataTableModelDict["titles"] = TableModel(data=[["Name", "Current Value", "New Value"]], header_labels=[], titles_set_window = True)
        self.tableViewDict["titles"].setModel(self.dataTableModelDict["titles"])
        self.tableViewDict["titles"].update()
        self.groupBox_for_titles.setFixedHeight(int(25 * (1 + 2)))
        self.verticalLayout_scrollingContents_properties.addWidget(self.groupBox_for_titles)

        # font for groupbox
        font_for_groupbox = QFont()
        font_for_groupbox.setBold(True)
        font_for_groupbox.setWeight(75)

        # create the group boxes
        for property in self.property_list:

            # init data list
            self.dataModelDict[property] = []

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

            # create table
            self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
            self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                       "    background-color: rgb(243, 243, 243);\n"
                                                       "    margin-top: 0;\n"
                                                       "}")
            self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
            self.tableViewDict[property].setFrameShadow(QFrame.Plain)
            self.tableViewDict[property].setDragEnabled(False)
            self.tableViewDict[property].setAlternatingRowColors(True)
            self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
            self.tableViewDict[property].setShowGrid(True)
            self.tableViewDict[property].setGridStyle(Qt.SolidLine)
            self.tableViewDict[property].setObjectName("tableView_general_information")
            self.tableViewDict[property].horizontalHeader().setVisible(False)
            self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
            self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
            self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
            self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
            self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.tableViewDict[property].verticalHeader().setVisible(False)
            self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
            self.tableViewDict[property].verticalHeader().setHighlightSections(False)
            self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
            self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
            self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
            self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
            self.tableViewDict[property].horizontalHeader().setStyleSheet("font-weight:bold; background-color: rgb(210, 210, 210);")
            self.tableViewDict[property].show()
            self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

            # fill table
            for field in self.field_dict[property]:
                self.dataModelDict[property].append([str(field), str(self.field_values_macro_dict["{}".format(property)][field]), str(self.field_values_macro_dict["{}".format(property)][field])])

            # update model
            self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[], three_column_window = True)
            self.tableViewDict[property].setModel(self.dataTableModelDict[property])
            self.tableViewDict[property].update()

            # update groupbox size in function of the number of rows
            self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

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

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        if "dBLM.TEST" not in self.current_device:
            self.current_selector = self.app.main_window.window_context.selector
        else:
            self.current_selector = ""

        # print
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

        # boolean
        types_are_wrong = False

        # iterate over all properties
        for property in self.property_list:

            # create dictionary to inject
            dict_to_inject = {}

            # init the boolean
            areAllFieldsJustTheSame = True

            # iterate over all fields
            for field_counter, field in enumerate(self.field_dict["{}".format(property)]):

                # compare old and new values
                old_value = self.field_values_macro_dict["{}".format(property)]["{}".format(field)]
                new_value = self.tableViewDict[property].model()._data[field_counter][2]

                # check if both are booleans
                if str(old_value) == "True" or str(old_value) == "False":
                    if str(new_value) != "True" and str(new_value) != "False":
                        types_are_wrong = True

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

        # check if the selector is generic
        if self.current_selector:
            isAllOrEmptySelector = self.current_selector.split(".")[-1] == "ALL"
        else:
            isAllOrEmptySelector = True

        # if the current selector is generic and there were changes on a non-mux channel, force the user to use a non-generic selector
        if muxAndNotEmpty and isAllOrEmptySelector:

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
        self.dialog_parent.getFunction(show_message = False)

        # close the dialog
        sleep(0.1)
        self._want_to_close = True
        self.close()
        self.deleteLater()

        # do another get
        if muxAndNotEmpty:
            self.dialog_parent.getFunction(show_message = False)

        # status bar message
        self.app.main_window.statusBar().showMessage("Command SET ran successfully!", 3*1000)
        self.app.main_window.statusBar().repaint()

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

        # get temp dir
        self.app_temp_dir = os.path.join(getSystemTempDir(), TEMP_DIR_NAME)

        # use this dict to store pyjapc subs data
        self.data_subs = {}

        # init boolean dict to optimize the subsCallback function
        self.firstReceivedSubsPyjapcData = {}

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

        # load selector
        self.LoadSelector()

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
        self.getFunction(show_message = False)

        # status bar message
        self.app.main_window.statusBar().showMessage("Settings panel of {} loaded successfully!".format(self.current_device), 10*1000)
        self.app.main_window.statusBar().repaint()

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
        self.tableViewDict = {}
        self.dataTableModelDict = {}
        self.dataModelDict = {}

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
                self.commandButtonDict["{}_{}".format("Commands", command)].setIcon(QIcon("icons/command.png"))
                self.commandButtonDict["{}_{}".format("Commands", command)].channel = "{}/{}".format(self.current_device, command)
                self.commandButtonDict["{}_{}".format("Commands", command)].setMinimumSize(QSize(120, 24))
                self.layoutDict["groupBox_{}".format("Commands")].addWidget(self.commandButtonDict["{}_{}".format("Commands", command)], row, column, 1, 1)

                # get the next field
                row += 1

        # create the group boxes
        for property in self.property_list:

            # init subs pyjapc boolean dict
            self.firstReceivedSubsPyjapcData[property] = False

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

                # use an empty selector for LHC devices
                if self.current_accelerator == "LHC":
                    selectorOverride = ""
                # use SPS.USER.ALL for SPS devices
                elif self.current_accelerator == "SPS":
                    selectorOverride = "SPS.USER.ALL"
                # use an empty selector for the others
                else:
                    selectorOverride = ""

                # create subs
                self.japc.subscribeParam("{}/{}".format(self.current_device, property), onValueReceived=self.subsCallback, onException=self.onException, timingSelectorOverride=selectorOverride)
                self.japc.startSubscriptions()

                # create table
                self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
                self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                                 "    background-color: rgb(243, 243, 243);\n"
                                                                 "    margin-top: 0;\n"
                                                                 "}")
                self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
                self.tableViewDict[property].setFrameShadow(QFrame.Plain)
                self.tableViewDict[property].setDragEnabled(False)
                self.tableViewDict[property].setAlternatingRowColors(True)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].setShowGrid(True)
                self.tableViewDict[property].setGridStyle(Qt.SolidLine)
                self.tableViewDict[property].setObjectName("tableView_general_information")
                self.tableViewDict[property].horizontalHeader().setVisible(False)
                self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
                self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
                self.tableViewDict[property].verticalHeader().setVisible(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
                self.tableViewDict[property].verticalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
                self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].setEditTriggers(QAbstractItemView.NoEditTriggers)
                self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
                self.tableViewDict[property].horizontalHeader().setStyleSheet(
                    "font-weight:bold; background-color: rgb(210, 210, 210);")
                self.tableViewDict[property].show()
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

            # in case the property is not multiplexed, create a GET kind of channel (i.e. use QLabel)
            else:

                # create table
                self.tableViewDict[property] = QTableView(self.groupBoxDict["{}".format(property)])
                self.tableViewDict[property].setStyleSheet("QTableView{\n"
                                                           "    background-color: rgb(243, 243, 243);\n"
                                                           "    margin-top: 0;\n"
                                                           "}")
                self.tableViewDict[property].setFrameShape(QFrame.StyledPanel)
                self.tableViewDict[property].setFrameShadow(QFrame.Plain)
                self.tableViewDict[property].setDragEnabled(False)
                self.tableViewDict[property].setAlternatingRowColors(True)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].setShowGrid(True)
                self.tableViewDict[property].setGridStyle(Qt.SolidLine)
                self.tableViewDict[property].setObjectName("tableView_general_information")
                self.tableViewDict[property].horizontalHeader().setVisible(False)
                self.tableViewDict[property].horizontalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setMinimumSectionSize(0)
                self.tableViewDict[property].horizontalHeader().setStretchLastSection(True)
                self.tableViewDict[property].horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
                self.tableViewDict[property].verticalHeader().setVisible(False)
                self.tableViewDict[property].verticalHeader().setDefaultSectionSize(25)
                self.tableViewDict[property].verticalHeader().setHighlightSections(False)
                self.tableViewDict[property].verticalHeader().setMinimumSectionSize(25)
                self.tableViewDict[property].verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.tableViewDict[property].setEditTriggers(QAbstractItemView.NoEditTriggers)
                self.tableViewDict[property].setFocusPolicy(Qt.NoFocus)
                self.tableViewDict[property].setSelectionMode(QAbstractItemView.NoSelection)
                self.tableViewDict[property].horizontalHeader().setFixedHeight(0)
                self.tableViewDict[property].horizontalHeader().setStyleSheet(
                    "font-weight:bold; background-color: rgb(210, 210, 210);")
                self.tableViewDict[property].show()
                self.layoutDict["groupBox_{}".format(property)].addWidget(self.tableViewDict[property])

        # set minimum dimensions for the main window according to the auto generated table
        self.setMinimumWidth(self.scrollArea_properties.sizeHint().width() * 2)
        self.setMinimumHeight(self.scrollArea_properties.sizeHint().height() * 1)

        # make the scroll bar of the get and set panel invisible
        sp_scroll_area_get_set = self.scrollArea_get_set.verticalScrollBar().sizePolicy()
        sp_scroll_area_get_set.setRetainSizeWhenHidden(True)
        self.scrollArea_get_set.verticalScrollBar().setSizePolicy(sp_scroll_area_get_set)
        self.scrollArea_get_set.verticalScrollBar().hide()

        return

    #----------------------------------------------#

    # function to receive pyjapc subs data
    def subsCallback(self, parameterName, dictValues, verbose = False):

        # get property name
        prop_name = parameterName.split("/")[1]

        # check that the values are different with respect to the previous iteration
        if self.firstReceivedSubsPyjapcData[prop_name]:
            if self.data_subs[prop_name] == dictValues:
                return

        # store the data
        self.data_subs[prop_name] = dictValues

        # update boolean
        self.firstReceivedSubsPyjapcData[prop_name] = True

        # print
        if verbose:
            print("{} - Received {} values...".format(UI_FILENAME, prop_name))

        return

    #----------------------------------------------#

    # function that handles pyjapc exceptions
    def onException(self, parameterName, description, exception, verbose = True):

        # print
        if verbose:
            print("{} - {}".format(UI_FILENAME, exception))

        # nothing
        pass

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # getters
        self.pushButton_get.clicked.connect(lambda: self.getFunction(show_message = True))

        # setters
        self.pushButton_set.clicked.connect(self.setFunction)

        # selector signal
        self.app.main_window.window_context.selectorChanged.connect(self.selectorWasChanged)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

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
    def getFunction(self, show_message = False):

        # print the GET action
        print("{} - Button GET pressed".format(UI_FILENAME))

        # create a field dictionary to see which fields changed
        self.field_values_macro_dict = {}

        # iterate over all properties
        for property in self.property_list:

            # init data list
            self.dataModelDict[property] = []

            # check if the property is multiplexed
            is_multiplexed = self.pyccda_dictionary[self.current_accelerator][self.current_device]["setting"][property]["mux"]

            # in case the property is multiplexed, the connection is via subscription so a GET is useless (i.e. skip it)
            if is_multiplexed == "True":

                # get the field values from the label text
                self.field_values_macro_dict["{}".format(property)] = {}

                # iterate over all fields
                for field in self.field_dict["{}".format(property)]:

                    # fill the dict and set text
                    try:
                        self.field_values_macro_dict["{}".format(property)][field] = self.data_subs[property][field]
                        self.dataModelDict[property].append([str(field), str(self.data_subs[property][field])])
                    except:
                        self.dataModelDict[property].append([str(field), "-"])

                # update model
                self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[])
                self.tableViewDict[property].setModel(self.dataTableModelDict[property])
                self.tableViewDict[property].update()

                # update groupbox size in function of the number of rows
                self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

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

                    # set text
                    self.dataModelDict[property].append([str(field), str(field_values[field])])

                # update model
                self.dataTableModelDict[property] = TableModel(data=self.dataModelDict[property], header_labels=[])
                self.tableViewDict[property].setModel(self.dataTableModelDict[property])
                self.tableViewDict[property].update()

                # update groupbox size in function of the number of rows
                self.groupBoxDict["{}".format(property)].setFixedHeight(int(25*(len(self.dataModelDict[property])+2)))

        # status bar message
        if show_message:
            self.app.main_window.statusBar().showMessage("Command GET ran successfully!", 3*1000)
            self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that sets the values into the fields
    def setFunction(self):

        # print the SET action
        print("{} - Button SET#1 pressed".format(UI_FILENAME))

        # get before set
        self.getFunction(show_message = False)

        # open the dialog
        self.dialog_three_column_set = DialogThreeColumnSet(parent = self)
        self.dialog_three_column_set.show()

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadSelector(self):

        # read current device
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt"), "r") as f:
                self.current_selector = f.read()

        return

    #----------------------------------------------#

    # function that loads the device from the aux txt file
    def LoadDeviceFromTxtPremain(self):

        # read current device
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt"), "r") as f:
                self.current_device = f.read()

        # read current accelerator
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt")):
            with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt"), "r") as f:
                self.current_accelerator = f.read()

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