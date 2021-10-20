########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, CApplication, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QBrush)
from PyQt5.QtCore import (QSize, Qt, QTimer, QThread, pyqtSignal, QObject)
from PyQt5.QtWidgets import (QSizePolicy)
from PyQt5.Qt import QItemSelectionModel

# OTHER IMPORTS

import sys
import os
from time import sleep
import pyccda
import pyjapc
import jpype as jp
from create_pyccda_json_file import create_pyccda_json_file
import json
import numpy as np

########################################################
########################################################

# GLOBALS

UI_FILENAME = "premain.ui"
QUERY = '((global==false) and (deviceClassInfo.name=="BLMDIAMONDVFC") and (timingDomain=="LHC" or timingDomain=="SPS")) or (name=="*dBLM.TEST*")'
RECHECK_DEVICES_PERIOD = 1*60 # each 1 minute

########################################################
########################################################

class GetWorkingDevicesThreadWorker(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(list, dict)

    #----------------------------------------------#

    # init function
    def __init__(self, device_list, acc_dev_list, japc, cern, old_working_devices, old_exception_dict):

        # inherit from QObject
        QObject.__init__(self)

        # declare attributes
        self.device_list = device_list
        self.acc_dev_list = acc_dev_list
        self.japc = japc
        self.cern = cern
        self.old_working_devices = old_working_devices
        self.old_exception_dict = old_exception_dict

        return

    #----------------------------------------------#

    # start function
    def start(self):

        # init the timer in terms of the RECHECK_DEVICES_PERIOD input variable (in seconds)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.getWorkingDevices)
        self._timer.start(RECHECK_DEVICES_PERIOD * 1000)

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # stop and emit the finish signal
        self._timer.stop()
        self.finished.emit()

        return

    #----------------------------------------------#

    # processing function
    def getWorkingDevices(self, verbose = False):

        # print thread address
        if verbose:
            print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))

        # declare the working devices list
        self.working_devices = []

        # save the exceptions in a dict
        self.exception_dict = {}

        # iterate over the devices
        for index_device, device in enumerate(self.device_list):

            # print the device for logging and debugging
            if verbose:
                print("{} - Checking the availability of {}".format(UI_FILENAME, device))

            # use an empty selector for LHC devices
            if self.acc_dev_list[index_device] == "LHC":
                selectorOverride = ""
            # use SPS.USER.ALL for SPS devices
            elif self.acc_dev_list[index_device] == "SPS":
                selectorOverride = "SPS.USER.SFTPRO1"
            # use an empty selector for the others
            else:
                selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "Capture", "rawBuf0"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

                # ignore in case that the exception was caused by the test device
                if str(device) != "dBLM.TEST4":

                    # print the exception
                    if verbose:
                        print("{} - Exception: cern.japc.core.ParameterException - {}".format(UI_FILENAME, xcp))
                        print("{} - Device {} is not working...".format(UI_FILENAME, device))

                    # save the exception as xcp
                    self.exception_dict[str(device)] = xcp

                    # continue to the next device
                    continue

            # append the device
            self.working_devices.append(device)

            # save the exception as empty
            self.exception_dict[str(device)] = ""

        # sleep the thread a bit
        QThread.sleep(5)

        # emit the signal that stores the working devices ONLY IF there were any changes
        if self.working_devices != self.old_working_devices:
            self.processed.emit(self.working_devices, self.exception_dict)

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

        # obtain all info about the devices via pyccda
        self.pyccda_dictionary = create_pyccda_json_file(query = QUERY, name_json_file = "pyccda_sps.json", verbose = False)

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # this is not implemented yet in ComRAD
        # self.app._rbac._startup_login_policy = rbac.CRbaStartupLoginPolicy.LOGIN_EXPLICIT
        # self.app._rbac.startup_login()

        # aux variable for the after-fully-loaded-comrad operations
        self.is_comrad_fully_loaded = False

        # import cern package for handling exceptions
        self.cern = jp.JPackage("cern")

        # set current accelerator
        self.current_accelerator = "SPS"

        # get the device list and the accelerator-device relation list
        self.device_list = []
        self.acc_dev_list = []
        for acc_counter, acc_name in enumerate(self.pyccda_dictionary):
            if acc_counter == 0:
                self.device_list = list(self.pyccda_dictionary[acc_name].keys())
                self.acc_dev_list = [acc_name]*len(list(self.pyccda_dictionary[acc_name].keys()))
            else:
                self.device_list += list(self.pyccda_dictionary[acc_name].keys())
                self.acc_dev_list += [acc_name]*len(list(self.pyccda_dictionary[acc_name].keys()))

        # order the device list
        self.acc_dev_list = [x for _, x in sorted(zip(self.device_list, self.acc_dev_list))]
        self.device_list.sort()

        # set current device
        self.current_device = ""

        # set the current window
        self.current_window = "premain"

        # create japc object
        self.japc = pyjapc.PyJapc()

        # get the devices that work
        self.getWorkingDevices(verbose = True)

        # remove the open device aux txt at startup
        if os.path.exists("aux_txts/open_new_device.txt"):
            os.remove("aux_txts/open_new_device.txt")

        # load the gui and set the title,
        print("{} - Loading the GUI file...".format(UI_FILENAME))
        super().__init__(*args, **kwargs)
        self.setWindowTitle("DIAMOND BLM EXPERT GUI")

        # init main window
        self.CEmbeddedDisplay.filename = ""

        # build the widgets and handle the signals
        print("{} - Building the code-only widgets...".format(UI_FILENAME))
        self.buildCodeWidgets()
        print("{} - Handling signals and slots...".format(UI_FILENAME))
        self.bindWidgets()

        # init the summary
        self.selectAndClickTheRoot()

        # at this point comrad should be fully loaded
        self.is_comrad_fully_loaded = True

        return

    #----------------------------------------------#

    # function that builds the widgets that weren't initialized using the UI qt designer file
    def buildCodeWidgets(self):

        # build the device-list treeview
        self.model = QStandardItemModel()
        self.treeView.setModel(self.model)
        self.createTreeFromDeviceList()
        self.treeView.header().hide()
        self.treeView.setUniformRowHeights(True)
        self.treeView.expandAll()

        return

    #----------------------------------------------#

    # function that initializes signal-slot dependencies
    def bindWidgets(self):

        # either shows the preview or the summary whenever an item from the treeview is clicked
        self.treeView.clicked.connect(self.itemFromTreeviewClicked)

        # close main device window when pressing the close toolbutton
        self.toolButton_main_close.clicked.connect(self.closeMain)

        # open settings window (mainly for the getters and setters)
        self.toolButton_main_settings.clicked.connect(self.goToSettingsWindow)

        # back to the last window (which can be preview or main)
        self.toolButton_main_back.clicked.connect(self.backToLastWindow)

        # set up a timer to open the devices when the OPEN DEVICE button is pressed
        self.timer_open_device = QTimer(self)
        self.timer_open_device.setInterval(1000)
        self.timer_open_device.timeout.connect(self.isOpenDevicePushButtonPressed)
        self.timer_open_device.start()

        # set up a timer to HACK comrad after it is fully loaded
        self.timer_hack_operations_after_comrad_is_fully_loaded = QTimer(self)
        self.timer_hack_operations_after_comrad_is_fully_loaded.setInterval(1000)
        self.timer_hack_operations_after_comrad_is_fully_loaded.timeout.connect(self.doOperationsAfterComradIsFullyLoaded)
        self.timer_hack_operations_after_comrad_is_fully_loaded.start()

        # selector signal
        self.app.main_window.window_context.selectorChanged.connect(self.selectorWasChanged)

        # rbac login signal
        self.app._rbac.login_succeeded.connect(self.rbacLoginSucceeded)

        # dunno if it works
        self.app._rbac._model.token_expired.connect(self.rbacLoginSucceeded)

        # rbac logout signal
        self.app._rbac.logout_finished.connect(self.rbacLogoutSucceeded)

        # recheck if the devices keep working in another thread
        self.aux_thread = QThread()
        self.aux_worker = GetWorkingDevicesThreadWorker(self.device_list, self.acc_dev_list, self.japc, self.cern, self.working_devices, self.exception_dict)
        self.aux_worker.moveToThread(self.aux_thread)
        self.aux_worker.finished.connect(self.finishThread)
        self.aux_thread.started.connect(self.aux_worker.start)
        self.aux_thread.start()

        # update the devices once the thread outputs the results
        self.aux_worker.processed.connect(self.updateWorkingDevices)

        return

    #----------------------------------------------#

    # function to handle thread stops
    def finishThread(self):

        # quit the thread
        self.aux_thread.quit()
        self.aux_thread.wait()

        return

    #----------------------------------------------#

    # function that handles japc and UI stuff when rbac is disconnected
    def rbacLogoutSucceeded(self):

        # print message
        print("{} - RBAC logout succeeded...".format(UI_FILENAME))

        # end pyjapc rbac connection
        self.japc.rbacLogout()

        # get working devices again
        self.getWorkingDevices(verbose = False)

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setIcon(QIcon("../icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("../icons/red_cross.png"))

        # update UI
        if self.current_window == "preview" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view)

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

        # get working devices again
        self.getWorkingDevices(verbose = False)

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setIcon(QIcon("../icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("../icons/red_cross.png"))

        # update UI (the preview panels)
        if self.current_window == "preview" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view)

        return

    #----------------------------------------------#

    # function that changes the current selector
    def selectorWasChanged(self):

        # change the current selector
        self.current_selector = self.app.main_window.window_context.selector
        print("{} - New selector is: {}".format(UI_FILENAME, self.current_selector))

        # update japc selector
        self.japc.setSelector(self.current_selector)

        return

    #----------------------------------------------#

    # function that checks which devices are properly working and which are not
    def getWorkingDevices(self, verbose = True):

        # declare the working devices list
        self.working_devices = []

        # save the exceptions in a dict
        self.exception_dict = {}

        # iterate over the devices
        for index_device, device in enumerate(self.device_list):

            # print the device for logging and debugging
            if verbose:
                print("{} - Checking the availability of {}".format(UI_FILENAME, device))

            # use an empty selector for LHC devices
            if self.acc_dev_list[index_device] == "LHC":
                selectorOverride = ""
            # use SPS.USER.ALL for SPS devices
            elif self.acc_dev_list[index_device] == "SPS":
                selectorOverride = "SPS.USER.SFTPRO1"
            # use an empty selector for the others
            else:
                selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "Capture", "rawBuf0"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

                # ignore in case that the exception was caused by the test device
                if str(device) != "dBLM.TEST4":

                    # print the exception
                    if verbose:
                        print("{} - Exception: cern.japc.core.ParameterException - {}".format(UI_FILENAME, xcp))
                        print("{} - Device {} is not working...".format(UI_FILENAME, device))

                    # save the exception as xcp
                    self.exception_dict[str(device)] = xcp

                    # continue to the next device
                    continue

            # append the device
            self.working_devices.append(device)

            # save the exception as empty
            self.exception_dict[str(device)] = ""

        return

    #----------------------------------------------#

    # function that updates the working devices (remember signal is only emitted when there are changes in the list)
    def updateWorkingDevices(self, working_devices, exception_dict):

        # print message
        print("{} - Uploading working devices!".format(UI_FILENAME))

        # update variables
        self.working_devices = working_devices
        self.exception_dict = exception_dict

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setIcon(QIcon("../icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon("../icons/red_cross.png"))

        # update UI (the preview panels)
        if self.current_window == "preview" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view)

        return

    #----------------------------------------------#

    # function that adds the items to the tree view
    def createTreeFromDeviceList(self):

        # init row and column counts
        self.model.setRowCount(0)
        self.model.setColumnCount(0)

        # create a root for every accelerator (LHC and SPS)
        for acc_counter, acc_name in enumerate(self.pyccda_dictionary):

            # set up the root
            root = QStandardItem(acc_name)

            # get accelerator specific devices
            acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == acc_name])

            # append items to the root
            for device in acc_device_list:

                # define the item to append
                itemToAppend = QStandardItem("{}".format(device))

                # determine the icon (working or not)
                if device in self.working_devices:
                    itemToAppend.setIcon(QIcon("../icons/green_tick.png"))
                else:
                    itemToAppend.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                    itemToAppend.setIcon(QIcon("../icons/red_cross.png"))

                # append it to the tree
                root.appendRow(itemToAppend)

            # append the root to the model
            self.model.appendRow(root)

            # get the index of the root (THIS HAS TO BE THE LAST LINE OF CODE AFTER THE TREE IS CREATED SO THAT THE INDEX ACTUALLY POINTS TO THE RIGHT ELEMENT OF THE TREE)
            if acc_counter == 0:
                self.index_of_the_root = root.index()

        return

    #----------------------------------------------#

    # function that selects and clicks the root (e.g. SPS) to init the summary
    def selectAndClickTheRoot(self):

        # initialize the summary by selecting and clicking the root
        self.treeView.selectionModel().select(self.index_of_the_root, QItemSelectionModel.Select)
        self.itemFromTreeviewClicked(self.index_of_the_root)

        return

    #----------------------------------------------#

    # function that shows the device preview when a device is clicked
    def itemFromTreeviewClicked(self, index):

        # store last index
        self.last_index_tree_view = index

        # read the name of the device
        item = self.treeView.selectedIndexes()[0]
        selected_text = str(item.model().itemFromIndex(index).text())
        print("{} - Clicked from treeView: {}".format(UI_FILENAME, selected_text))

        # if the item IS NOT the root, then show the preview
        if selected_text != "SPS" and selected_text != "LHC":

            # get the parent (cycle) text (e.g. LHC or SPS)
            parent_text = str(item.model().itemFromIndex(index).parent().text())

            # update selector
            if parent_text == "SPS":
                self.app.main_window.window_context.selector = 'SPS.USER.ALL'
            elif parent_text == "LHC":
                self.app.main_window.window_context.selector = 'LHC.USER.ALL'

            # update the current device
            self.current_device = selected_text
            self.current_accelerator = parent_text
            self.writeDeviceIntoTxtForMainScreen(self.current_accelerator)

            # update text label
            if self.current_device in self.working_devices:
                self.label_device_panel.setText("DEVICE PANEL <font color=green>{}</font> : <font color=green>{}</font>".format(parent_text, self.current_device))
            else:
                self.label_device_panel.setText( "DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format(parent_text, self.current_device))

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_one_device.py"
            self.CEmbeddedDisplay.open_file(force=True)

            # enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_main_close.setEnabled(True)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "preview"

        # if the item IS the root, then show the summary
        else:

            # update selector
            if selected_text == "SPS":
                self.app.main_window.window_context.selector = 'SPS.USER.ALL'
            elif selected_text == "LHC":
                self.app.main_window.window_context.selector = 'LHC.USER.ALL'

            # send and write the device list
            self.current_accelerator = selected_text
            self.writeDeviceListIntoTxtForSummary(self.current_accelerator)

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=black>{}</font> : <font color=black>{}</font>".format(selected_text, "SUMMARY"))

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_summary.py"
            self.CEmbeddedDisplay.open_file(force=True)

            # enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_main_close.setEnabled(True)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "summary"

    #----------------------------------------------#

    # function that closes the main device window
    def closeMain(self):

        # print the action
        print("{} - Button CLOSE pressed".format(UI_FILENAME))

        # close main container
        if self.CEmbeddedDisplay.filename != "":

            # update main panel
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format("NO CYCLE SELECTED", "NO DEVICE SELECTED"))

            # disable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_main_close.setEnabled(False)
            self.toolButton_main_back.setEnabled(False)

            # update the current window
            self.current_window = "premain"

            # reset last index
            self.last_index_tree_view = 0

        return

    #----------------------------------------------#

    # function that opens the settings window that shows the different configurable parameters of the device
    def goToSettingsWindow(self):

        # print the action
        print("{} - Button SETTINGS pressed".format(UI_FILENAME))

        # open settings window
        if self.CEmbeddedDisplay.filename != "":

            # update main panel
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "settings_dialog_auto.py"
            self.CEmbeddedDisplay.open_file(force=True)

            # disable and enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_main_close.setEnabled(True)
            self.toolButton_main_back.setEnabled(True)

            # update the current window
            self.current_window = "settings"

    #----------------------------------------------#

    # function that re-opens the last window
    def backToLastWindow(self):

        # print the action
        print("{} - Button BACK pressed".format(UI_FILENAME))

        # if you were in settings, go back to main
        if self.current_window == "settings":

            # check you are not in premain
            if self.CEmbeddedDisplay.filename != "":

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file(force=True)

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        # if you were in main, go back to preview
        elif self.current_window == "main":

            # check you are not in premain
            if self.CEmbeddedDisplay.filename != "":

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "preview_one_device.py"
                self.CEmbeddedDisplay.open_file(force=True)

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(False)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(False)

                # update the current window
                self.current_window = "preview"

        return

    #----------------------------------------------#

    # function that checks if the OPEN DEVICE button was pressed and open the device in case it was
    def isOpenDevicePushButtonPressed(self):

        # check if txt exists
        if os.path.exists("aux_txts/open_new_device.txt"):

            # init the boolean
            wasTheButtonPressed = "False"

            # open it
            with open("aux_txts/open_new_device.txt", "r") as f:

                # read it
                wasTheButtonPressed = f.read()

            # if the button was pressed then open the device panel
            if wasTheButtonPressed == "True":

                # remove the file because we already know we have to open the device
                os.remove("aux_txts/open_new_device.txt")

                # open main container
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file(force=True)

                # enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        return

    #----------------------------------------------#

    # function that writes the device name into a txt file
    def writeDeviceIntoTxtForMainScreen(self, acc_name):

        # create the dir in case it does not exist
        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        # write the current device
        with open("aux_txts/current_device_premain.txt", "w") as f:
            f.write(str(self.current_device))

        # write the current accelerator
        with open("aux_txts/current_accelerator_premain.txt", "w") as f:
            f.write(str(acc_name))

        # write the exception of the current device
        with open("aux_txts/exception_premain.txt", "w") as f:
            f.write("{}\n".format(self.exception_dict[str(self.current_device)]))

        return

    #----------------------------------------------#

    # function that writes the device list into a txt so that the summary python file can read it
    def writeDeviceListIntoTxtForSummary(self, acc_name):

        # get accelerator specific devices
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == acc_name])

        # create the dir in case it does not exist
        if not os.path.exists("aux_txts"):
            os.mkdir("aux_txts")

        # write the file: device_list_premain
        with open("aux_txts/device_list_premain.txt", "w") as f:
            for dev in acc_device_list:
                f.write("{}\n".format(dev))

        # write the file: working_devices_premain
        with open("aux_txts/working_devices_premain.txt", "w") as f:
            for dev in self.working_devices:
                f.write("{}\n".format(dev))

        return

    #----------------------------------------------#

    # function that does all operations that are required after comrad is fully loaded
    def doOperationsAfterComradIsFullyLoaded(self):

        # click the root and stop the timer when comrad is fully loaded
        if self.is_comrad_fully_loaded:

            # click the root
            self.selectAndClickTheRoot()

            # change the title of the app
            self.app.main_window.setWindowTitle("DIAMOND BLM EXPERT GUI")

            # change the logo
            self.app.main_window.setWindowIcon(QIcon("../icons/diamond_2.png"))

            # hide the log console (not needed when using launcher.py)
            # self.app.main_window.hide_log_console()

            # finally stop the timer
            self.timer_hack_operations_after_comrad_is_fully_loaded.stop()

        return

    #----------------------------------------------#

    # iterator function to iterate over treeview rows
    def iterItems(self, root):
        if root is not None:
            for row in range(root.rowCount()):
                row_item = root.child(row, 0)
                if row_item.hasChildren():
                    for childIndex in range(row_item.rowCount()):
                        child = row_item.child(childIndex, 0)
                        yield child

    #----------------------------------------------#

########################################################
########################################################