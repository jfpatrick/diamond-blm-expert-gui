########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# COMRAD AND PYQT IMPORTS

from comrad import (CDisplay, CApplication, PyDMChannelDataSource, CurveData, PointData, PlottingItemData, TimestampMarkerData, TimestampMarkerCollectionData, UpdateSource, rbac)
from PyQt5.QtGui import (QIcon, QColor, QGuiApplication, QCursor, QStandardItemModel, QStandardItem, QBrush, QPixmap)
from PyQt5.QtCore import (QSize, Qt, QTimer, QThread, pyqtSignal, QObject, QEventLoop, QCoreApplication)
from PyQt5.QtWidgets import (QSizePolicy, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget, QProgressDialog)
from PyQt5.Qt import QItemSelectionModel, QMenu

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
import shutil
import faulthandler
from general_utils import createCustomTempDir, getSystemTempDir
from datetime import datetime, timedelta, timezone

########################################################
########################################################

# GLOBALS

TEMP_DIR_NAME = "temp_diamond_blm_expert_gui"
SAVING_PATH = "/user/bdisoft/development/python/gui/deployments-martinja/diamond-blm-expert-gui"
UI_FILENAME = "premain.ui"
QUERY = '((global==false) and (deviceClassInfo.name=="BLMDIAMONDVFC") and (timingDomain=="LHC" or timingDomain=="SPS")) or (name=="*dBLM.TEST*")'
RECHECK_DEVICES_PERIOD = 1*6000 # each 1 minute

########################################################
########################################################

class workingModesThreadWorker(QObject):

    #----------------------------------------------#

    # signals
    finished = pyqtSignal()
    processed = pyqtSignal(dict, dict)

    #----------------------------------------------#

    # init function
    def __init__(self, current_device, current_accelerator, japc, property_list, cern):

        # inherit from QObject
        QObject.__init__(self)

        # declare attributes
        self.current_device = current_device
        self.current_accelerator = current_accelerator
        self.japc = japc
        self.property_list = property_list
        self.cern = cern
        self.exit_boolean = False

        return

    #----------------------------------------------#

    # stop function
    def stop(self):

        # update stop variable
        self.exit_boolean = True

        # emit the finish signal
        self.finished.emit()

        return

    #----------------------------------------------#

    # processing function
    def start(self, verbose = False):

        # print thread address
        if verbose:
            print("{} - Processing thread: {}".format(UI_FILENAME, QThread.currentThread()))

        # init the data model dict for the working modules table
        self.modules_data = {}

        # store full errors
        self.errors = {}

        # selectorOverride for the working modules table has to be a specific selector
        # use an empty selector for LHC devices
        if self.current_accelerator == "LHC":
            selectorOverride = ""
        # use SPS.USER.ALL for SPS devices
        elif self.current_accelerator == "SPS":
            selectorOverride = "SPS.USER.SFTPRO1"
        # use an empty selector for the others
        else:
            selectorOverride = ""

        # do a first GET to get NTURNS
        try:

            # in the LHC, 11245 turns is 1 second (rule of three)
            nturns = float(self.japc.getParam("{}/{}#blmNTurn".format(self.current_device, "BeamLossHistogramSetting"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False))
            turn_time_in_seconds = nturns / 11245
            possible_error_in_seconds = 0.25

        # if this does not work, then nothing should be working (NO_DATA_AVAILABLE_FOR_USER likely)
        except:

            # pass
            pass

        # counter for the while
        counter_property = 0

        # continuously analyze the modes until stop is called
        while not self.exit_boolean:

            # property declaration
            if counter_property == len(self.property_list):
                counter_property = 0
            property = self.property_list[counter_property]

            print("HOLA: {}".format(property))

            # skip general information property
            if property == "GeneralInformation":
                counter_property += 1
                continue

            # do a GET request via japc
            try:

                # get the fields
                field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)

                # get timestamps
                get_ts = field_values[1]["acqStamp"]
                current_ts = datetime.now(timezone.utc)

                # for the capture do not care about timestamps
                if property == "Capture":

                    # if the buffer is not empty
                    if field_values[0]["rawBuf0"].size > 0:

                        # if the try did not give an error then it is working
                        self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                        self.errors[property] = "-"

                    # if buffers are empty show a custom error
                    else:

                        # BUFFERS_ARE_EMPTY
                        self.modules_data[property] = [property, "No", "BUFFERS_ARE_EMPTY", "{}".format(str(get_ts))]
                        self.errors[property] = "custom.message.error: BUFFERS_ARE_EMPTY: The buffers of the Capture property are empty arrays."

                # for the others we should care about timestamps
                else:

                    # show a custom error if nturns is 0
                    if nturns == 0:

                        # NTURNS_IS_ZERO
                        self.modules_data[property] = [property, "No", "NTURNS_IS_ZERO", "{}".format(str(get_ts))]
                        self.errors[property] = "custom.message.error: NTURNS_IS_ZERO: The field nturns is 0 and hence the mode is not working."

                    # normal procedure
                    else:

                        # compare timestamps
                        if current_ts - get_ts < timedelta(seconds = turn_time_in_seconds + possible_error_in_seconds):

                            # sleep a little bit
                            QThread.msleep(int(turn_time_in_seconds*1000 + possible_error_in_seconds*1000))

                            # do a second GET
                            field_values = self.japc.getParam("{}/{}".format(self.current_device, property), timingSelectorOverride=selectorOverride, getHeader=True, noPyConversion=False)
                            get_ts = field_values[1]["acqStamp"]
                            current_ts = datetime.now(timezone.utc)

                            # compare timestamps again
                            if current_ts - get_ts < timedelta(seconds = turn_time_in_seconds + possible_error_in_seconds):

                                # WORKING MODE
                                self.modules_data[property] = [property, "Yes", "-", "{}".format(str(get_ts))]
                                self.errors[property] = "-"

                            # 2nd check still too old
                            else:

                                # TS_TOO_OLD
                                self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
                                self.errors[property] = "custom.message.error.2nd.check: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds + possible_error_in_seconds, current_ts)

                        # 1st check too old
                        else:

                            # TS_TOO_OLD
                            self.modules_data[property] = [property, "No", "TS_TOO_OLD", "{}".format(str(get_ts))]
                            self.errors[property] = "custom.message.error.1st.check: TS_TOO_OLD: The ({}) timestamp of the GET call is at least {} seconds older than the current ({}) timestamp.".format(get_ts, turn_time_in_seconds + possible_error_in_seconds, current_ts)

            # this exception is usually NO_DATA_AVAILABLE_FOR_USER (happens when it is not initialized yet)
            except self.cern.japc.core.ParameterException as xcp:

                # NO_DATA_AVAILABLE_FOR_USER
                self.modules_data[property] = [property, "No", str(xcp.getMessage()).split(":")[0], "-"]
                self.errors[property] = str(xcp)

            # next iter
            counter_property += 1

            # emit the signal
            self.processed.emit(self.modules_data, self.errors)

            # sleep the thread a bit
            QThread.msleep(100)

        return

    #----------------------------------------------#

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

            # # use an empty selector for LHC devices
            # if self.acc_dev_list[index_device] == "LHC":
            #     selectorOverride = ""
            # # use SPS.USER.ALL for SPS devices
            # elif self.acc_dev_list[index_device] == "SPS":
            #     selectorOverride = "SPS.USER.SFTPRO1"
            # # use an empty selector for the others
            # else:
            #     selectorOverride = ""

            # use empty selector for GeneralInformation
            selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "GeneralInformation", "AutoGain"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

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

        # use faulthandler to debug segmentation faults
        # faulthandler.enable()

        # init aux for qthread
        self.aux_thread_for_preview_one_device = 0

        # create the temporary directory to store all the aux variables
        self.app_temp_dir = createCustomTempDir(TEMP_DIR_NAME)

        # init last index
        self.last_index_tree_view = 0

        # obtain all info about the devices via pyccda
        self.pyccda_dictionary = create_pyccda_json_file(query = QUERY, name_json_file = "pyccda_config.json", dir_json = self.app_temp_dir, verbose = False)

        # retrieve the app CApplication variable
        self.app = CApplication.instance()

        # status bar message
        self.app.main_window.statusBar().showMessage("Loading main application window...", 0)
        self.app.main_window.statusBar().repaint()

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
        self.current_device = "SP.BA1.BLMDIAMOND.2"

        # set the current window
        self.current_window = "premain"

        # create japc object
        self.japc = pyjapc.PyJapc()

        # get the devices that work
        self.getWorkingDevices(verbose = True)

        # init preloaded devices to show or not the progress dialog on preview_one_device.py
        self.preloaded_devices = set()

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
        # self.selectAndClickTheRoot()

        # at this point comrad should be fully loaded
        self.is_comrad_fully_loaded = True

        # status bar message
        self.app.main_window.statusBar().clearMessage()
        self.app.main_window.statusBar().repaint()

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

        # set up the right-click menu handler
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openRightClickTreeMenu)

        return

    #----------------------------------------------#

    # this function sets up the menu that is opened when right-clicking the tree
    def openRightClickTreeMenu(self, position):

        # get the clicked element
        indexes = self.treeView.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            item = self.treeView.selectedIndexes()[0]
            selected_device = str(item.model().itemFromIndex(index).text())
            if selected_device != "SPS" and selected_device != "LHC" and selected_device != "NONE":
                selected_accelerator = str(item.model().itemFromIndex(index).parent().text())
            else:
                first_device = str(item.model().itemFromIndex(index).child(0,0).text())
                selected_accelerator = selected_device
                selected_device = ""
            while index.parent().isValid():
                index = index.parent()
                level += 1

        # create the menu
        menu = QMenu()

        # if the accelerator was selected get the commands of the first device
        if selected_device == "":
            command_list = list(self.pyccda_dictionary[selected_accelerator][first_device]["command"].keys())
        else:
            command_list = list(self.pyccda_dictionary[selected_accelerator][selected_device]["command"].keys())

        # init dict
        self.command_dict = {}

        # level 0 is either LHC or SPS (or NONE)
        if level == 0:
            for command in command_list:
                self.command_dict[command] = menu.addAction(self.tr("Run {} on all {} devices".format(command, selected_accelerator)))
                self.command_dict[command].triggered.connect(lambda: self.commandActionAll(selected_accelerator))

        # level 1 are individual devices
        elif level == 1:
            for command in command_list:
                self.command_dict[command] = menu.addAction(self.tr("Run {} on {}".format(command, selected_device)))
                self.command_dict[command].triggered.connect(lambda: self.commandAction(selected_device))

        # update view
        menu.exec_(self.treeView.viewport().mapToGlobal(position))

        return

    #----------------------------------------------#

    # function that runs the selected command on all the acc devices
    def commandActionAll(self, selected_accelerator):

        # get command name
        command = self.sender().text().split(" ")[1]

        # print
        print("{} - Running command {} on all {} devices...".format(UI_FILENAME, command, selected_accelerator))

        # get device list
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == selected_accelerator])

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # init progress bar
        counter_device = 0
        self.progress_dialog_all_commands = QProgressDialog("Running command {} on all {} devices...".format(command, selected_accelerator), None, 0, len(acc_device_list))
        self.progress_dialog_all_commands.setAutoClose(False)
        self.progress_dialog_all_commands.setWindowTitle("Progress")
        self.progress_dialog_all_commands.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))
        self.progress_dialog_all_commands.show()
        self.progress_dialog_all_commands.repaint()

        # iterate over devices
        for counter_device, selected_device in enumerate(acc_device_list):

            # update progress bar
            self.progress_dialog_all_commands.setValue(counter_device)
            self.progress_dialog_all_commands.repaint()
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # status bar message
            self.app.main_window.statusBar().showMessage("Running command {} on all {} devices ({}/{})...".format(command, selected_accelerator, counter_device+1, len(acc_device_list)), 0)
            self.app.main_window.statusBar().repaint()

            # send an empty dict to perform a COMMAND operation via pyjapc
            try:
                self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
            except Exception as xcp:
                exception = xcp
                print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
                exception_dev_list.append(selected_device)

        # close progress bar
        self.progress_dialog_all_commands.close()

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running command {} on all {} devices!".format(command, selected_accelerator), 10*1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command {}".format(command)
            message_text = "Command {} ran successfully on all {} devices.".format(command, selected_accelerator)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            if len(exception_dev_list) == len(acc_device_list):
                message_title = "Command {}".format(command)
                message_text = "Unable to run command {} on any of the {} devices.".format(command, selected_accelerator)
                self.message_box = QMessageBox.critical(self, message_title, message_text)
            else:
                message_title = "Command {}".format(command)
                message_text = "Unable to run command {} on the following devices: {}. Command ran successfully in the others though.".format(command, ', '.join(exception_dev_list))
                self.message_box = QMessageBox.critical(self, message_title, message_text)

        return

    #----------------------------------------------#

    # function that runs the selected command on the selected device
    def commandAction(self, selected_device):

        # get command name
        command = self.sender().text().split(" ")[1]

        # status bar message
        self.app.main_window.statusBar().showMessage("Running command {} on {}...".format(command, selected_device), 0)
        self.app.main_window.statusBar().repaint()

        # print
        print("{} - Running command {} on {}...".format(UI_FILENAME, command, selected_device))

        # save exceptions here
        exception_dev_list = []
        exception = ""

        # send an empty dict to perform a COMMAND operation via pyjapc
        try:
            self.japc.setParam("{}/{}".format(selected_device, command), {}, timingSelectorOverride="")
        except Exception as xcp:
            exception = xcp
            print("{} - Unable to run the command: {}".format(UI_FILENAME, exception))
            exception_dev_list.append(selected_device)

        # status bar message
        self.app.main_window.statusBar().showMessage("Finished running command {} on {}!".format(command, selected_device), 10*1000)
        self.app.main_window.statusBar().repaint()

        # show finish message
        if not exception_dev_list:
            message_title = "Command {}".format(command)
            message_text = "Command {} ran successfully on {}.".format(command, selected_device)
            self.message_box = QMessageBox.information(self, message_title, message_text)
        else:
            message_title = "Command {}".format(command)
            message_text = "Unable to run command {} on {} due to the following exception: {}".format(command, selected_device, exception)
            self.message_box = QMessageBox.critical(self, message_title, message_text)

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

        # send freeze information when pressing the freeze toolbutton
        self.toolButton_freeze.toggled.connect(self.sendFreezeText)

        # set up a timer to open the devices when the OPEN DEVICE button is pressed
        self.timer_open_device = QTimer(self)
        self.timer_open_device.setInterval(1000)
        self.timer_open_device.timeout.connect(self.isOpenDevicePushButtonPressed)
        self.timer_open_device.start()

        # set up a timer to HACK comrad after it is fully loaded
        self.timer_hack_operations_after_comrad_is_fully_loaded = QTimer(self)
        self.timer_hack_operations_after_comrad_is_fully_loaded.setInterval(100)
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

    # function to handle thread stops
    def finishThreadPreviewOneDevice(self):

        # quit the thread
        self.aux_thread_for_preview_one_device.quit()
        self.aux_thread_for_preview_one_device.wait()

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
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/red_cross.png"))

        # update UI
        if self.current_window == "preview" or self.current_window == "summary" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

        return

    #----------------------------------------------#

    # this function gets activated whenever RBAC logins successfully
    def rbacLoginSucceeded(self):

        # progress bar init
        counter_device = 0
        self.progress_dialog_after_rbac = QProgressDialog("Updating devices after a successful RBAC login...", None, 0, len(self.device_list))
        self.progress_dialog_after_rbac.setAutoClose(False)
        self.progress_dialog_after_rbac.setWindowTitle("Progress")
        self.progress_dialog_after_rbac.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))
        self.progress_dialog_after_rbac.show()
        self.progress_dialog_after_rbac.repaint()

        # print message
        print("{} - RBAC login succeeded...".format(UI_FILENAME))

        # save the token into the environmental variable so that we can read it with pyjapc
        os.environ["RBAC_TOKEN_SERIALIZED"] = self.app._rbac.serialized_token

        # now that we have a token try to login with japc too
        self.japc.rbacLogin(readEnv=True)

        # get working devices again
        self.getWorkingDevices(verbose = False, from_rbac = True)

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/red_cross.png"))

        # close progress bar
        self.progress_dialog_after_rbac.close()

        # update UI (the preview panels)
        if self.current_window == "preview" or self.current_window == "summary" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

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
    def getWorkingDevices(self, verbose = True, from_rbac = False):

        # declare the working devices list
        self.working_devices = []

        # save the exceptions in a dict
        self.exception_dict = {}

        # iterate over the devices
        for index_device, device in enumerate(self.device_list):

            # status bar message
            if from_rbac:
                self.app.main_window.statusBar().showMessage("Successful RBAC login! Checking availability of new devices ({}/{})...".format(index_device+1, len(self.device_list)), 0)
                self.app.main_window.statusBar().repaint()
                self.progress_dialog_after_rbac.setValue(index_device)
                self.progress_dialog_after_rbac.repaint()
                self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

            # print the device for logging and debugging
            if verbose:
                print("{} - Checking the availability of {}".format(UI_FILENAME, device))

            # # use an empty selector for LHC devices
            # if self.acc_dev_list[index_device] == "LHC":
            #     selectorOverride = ""
            # # use SPS.USER.ALL for SPS devices
            # elif self.acc_dev_list[index_device] == "SPS":
            #     selectorOverride = "SPS.USER.SFTPRO1"
            # # use an empty selector for the others
            # else:
            #     selectorOverride = ""

            # use empty selector for GeneralInformation
            selectorOverride = ""

            # try out if japc returns an error or not
            try:

                # try to acquire the data from pyjapc
                all_data_from_pyjapc = self.japc.getParam("{}/{}#{}".format(device, "GeneralInformation", "AutoGain"), timingSelectorOverride=selectorOverride, getHeader=False, noPyConversion=False)

            # in case we get an exception, don't add the device to the working list
            except self.cern.japc.core.ParameterException as xcp:

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

        # status bar message
        if from_rbac:
            self.app.main_window.statusBar().showMessage("Device availability check finished! {}/{} devices working right now!".format(len(self.working_devices), len(self.device_list)), 10*1000)
            self.app.main_window.statusBar().repaint()

        return

    #----------------------------------------------#

    # function that updates the working devices (remember signal is only emitted when there are changes in the list)
    def updateWorkingDevices(self, working_devices, exception_dict, verbose = False):

        # print message
        if verbose:
            print("{} - Updating working devices!".format(UI_FILENAME))

        # update variables
        self.working_devices = working_devices
        self.exception_dict = exception_dict

        # update UI (tree icons and stuff like that)
        for item in self.iterItems(self.model.invisibleRootItem()):
            if str(item.data(role=Qt.DisplayRole)) in self.working_devices:
                item.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/green_tick.png"))
            else:
                item.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                item.setIcon(QIcon(SAVING_PATH + "/icons/red_cross.png"))

        # update UI (the preview panels)
        if self.current_window == "preview" or self.current_window == "premain":
            if self.last_index_tree_view != 0:
                self.itemFromTreeviewClicked(index=self.last_index_tree_view, ignore_checking=True)

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
                    itemToAppend.setForeground(QBrush(Qt.black, Qt.SolidPattern))
                    itemToAppend.setIcon(QIcon(SAVING_PATH + "/icons/green_tick.png"))
                else:
                    itemToAppend.setForeground(QBrush(Qt.red, Qt.SolidPattern))
                    itemToAppend.setIcon(QIcon(SAVING_PATH + "/icons/red_cross.png"))

                # append it to the tree
                root.appendRow(itemToAppend)

            # append the root to the model
            self.model.appendRow(root)

            # get the index of the root (THIS HAS TO BE THE LAST LINE OF CODE AFTER THE TREE IS CREATED SO THAT THE INDEX ACTUALLY POINTS TO THE RIGHT ELEMENT OF THE TREE)
            if acc_counter == 0:
                self.index_of_the_root = root.index()

        return

    #----------------------------------------------#

    # function that selects and clicks the root (e.g. SPS) to init tshe summary
    def selectAndClickTheRoot(self):

        # initialize the summary by selecting and clicking the root
        self.treeView.selectionModel().select(self.index_of_the_root, QItemSelectionModel.Select)
        self.itemFromTreeviewClicked(self.index_of_the_root, ignore_checking = True)

        return

    #----------------------------------------------#

    # function that shows the device preview when a device is clicked
    def itemFromTreeviewClicked(self, index, ignore_checking = False):

        # if the user clicked the same just skip
        if not ignore_checking:
            if index == self.last_index_tree_view:
                return

        # store last index
        self.last_index_tree_view = index

        # read the name of the device
        item = self.treeView.selectedIndexes()[0]
        selected_text = str(item.model().itemFromIndex(index).text())
        print("{} - Clicked from treeView: {}".format(UI_FILENAME, selected_text))

        # if the item IS NOT the root, then show the preview
        if selected_text != "SPS" and selected_text != "LHC" and selected_text != "NONE":

            # get the parent (cycle) text (e.g. LHC or SPS)
            parent_text = str(item.model().itemFromIndex(index).parent().text())

            # update selector
            if parent_text == "SPS":
                self.app.main_window.window_context.selector = 'SPS.USER.ALL'
            elif parent_text == "LHC":
                self.app.main_window.window_context.selector = ''
            elif parent_text == "NONE":
                self.app.main_window.window_context.selector = ''

            # update the current device
            self.current_device = selected_text
            self.current_accelerator = parent_text
            self.preloaded_devices.add(self.current_device)
            self.writeDeviceIntoTxtForSubWindows(self.current_accelerator)

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading device preview...", 0)
            self.app.main_window.statusBar().repaint()

            # clear for new device
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "modules_data_for_preview_one_device.json")):
                os.remove(os.path.join(self.app_temp_dir, "aux_jsons", "modules_data_for_preview_one_device.json"))
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons", "errors_for_preview_one_device.json")):
                os.remove(os.path.join(self.app_temp_dir, "aux_jsons", "errors_for_preview_one_device.json"))

            # stop old thread
            if type(self.aux_thread_for_preview_one_device) == QThread:
                if self.aux_thread_for_preview_one_device.isRunning():
                    self.aux_worker_for_preview_one_device.stop()

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_one_device.py"
            self.CEmbeddedDisplay.open_file()

            # get the property list
            self.property_list = list(self.pyccda_dictionary[self.current_accelerator][self.current_device]["acquisition"].keys())

            # order the property list
            self.property_list.sort()

            # recheck if the modes are working each x seconds
            self.aux_thread_for_preview_one_device = QThread(parent=self)
            self.aux_worker_for_preview_one_device = workingModesThreadWorker(self.current_device, self.current_accelerator, self.japc, self.property_list, self.cern)
            self.aux_worker_for_preview_one_device.moveToThread(self.aux_thread_for_preview_one_device)
            self.aux_worker_for_preview_one_device.finished.connect(self.finishThreadPreviewOneDevice)
            self.aux_thread_for_preview_one_device.started.connect(self.aux_worker_for_preview_one_device.start)
            self.aux_thread_for_preview_one_device.start()

            # update once the thread outputs the results
            self.aux_worker_for_preview_one_device.processed.connect(self.sendUpdatesWorkingModes)

            # update text label
            if self.current_device in self.working_devices:
                self.label_device_panel.setText("DEVICE PANEL <font color=green>{}</font> : <font color=green>{}</font>".format(parent_text, self.current_device))
            else:
                self.label_device_panel.setText( "DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format(parent_text, self.current_device))

            # enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
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
                self.app.main_window.window_context.selector = ''
            elif selected_text == "NONE":
                self.app.main_window.window_context.selector = ''

            # send and write the device list
            self.current_accelerator = selected_text
            for pre_dev in list(np.array(self.device_list)[np.array(self.acc_dev_list) == self.current_accelerator]):
                self.preloaded_devices.add(pre_dev)
            self.writeDeviceIntoTxtForSubWindows(self.current_accelerator)

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading {} summary preview...".format(self.current_accelerator), 0)
            self.app.main_window.statusBar().repaint()

            # open main container
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "preview_summary.py"
            self.CEmbeddedDisplay.open_file()

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=black>{}</font> : <font color=black>{}</font>".format(selected_text, "SUMMARY"))

            # enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
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

            # status bar message
            self.app.main_window.statusBar().showMessage("Main window closed!", 5*1000)
            self.app.main_window.statusBar().repaint()

            # update main panel
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()

            # update text label
            self.label_device_panel.setText("DEVICE PANEL <font color=red>{}</font> : <font color=red>{}</font>".format("NO CYCLE SELECTED", "NO DEVICE SELECTED"))

            # disable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
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

        # write the selector
        self.writeSelectorIntoTxt()

        # open settings window
        if self.CEmbeddedDisplay.filename != "":

            # status bar message
            self.app.main_window.statusBar().showMessage("Loading settings...", 0)
            self.app.main_window.statusBar().repaint()

            # update main panel
            self.CEmbeddedDisplay.filename = ""
            self.CEmbeddedDisplay.hide()
            self.CEmbeddedDisplay.show()
            self.CEmbeddedDisplay.filename = "settings_dialog_auto.py"
            self.CEmbeddedDisplay.open_file()

            # disable and enable tool buttons
            self.toolButton_main_settings.setEnabled(False)
            self.toolButton_freeze.setEnabled(False)
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

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device window...", 0)
                self.app.main_window.statusBar().repaint()

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file()

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_freeze.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        # if you were in main, go back to preview
        elif self.current_window == "main":

            # check you are not in premain
            if self.CEmbeddedDisplay.filename != "":

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device preview...", 0)
                self.app.main_window.statusBar().repaint()

                # update main panel
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "preview_one_device.py"
                self.CEmbeddedDisplay.open_file()

                # disable and enable tool buttons
                self.toolButton_main_settings.setEnabled(False)
                self.toolButton_freeze.setEnabled(False)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(False)

                # update the current window
                self.current_window = "preview"

        return

    #----------------------------------------------#

    # function that checks if the OPEN DEVICE button was pressed and open the device in case it was
    def isOpenDevicePushButtonPressed(self):

        # check if txt exists
        if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt")):

            # init the boolean
            wasTheButtonPressed = "False"

            # open it
            with open(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt"), "r") as f:
                wasTheButtonPressed = f.read()

            # if the button was pressed then open the device panel
            if wasTheButtonPressed == "True":

                # remove the file because we already know we have to open the device
                os.remove(os.path.join(self.app_temp_dir, "aux_txts", "open_new_device.txt"))

                # status bar message
                self.app.main_window.statusBar().showMessage("Loading device window...", 0)
                self.app.main_window.statusBar().repaint()

                # open main container
                self.CEmbeddedDisplay.filename = ""
                self.CEmbeddedDisplay.hide()
                self.CEmbeddedDisplay.show()
                self.CEmbeddedDisplay.filename = "main_auto.py"
                self.CEmbeddedDisplay.open_file()

                # enable tool buttons
                self.toolButton_main_settings.setEnabled(True)
                self.toolButton_freeze.setEnabled(True)
                self.toolButton_main_close.setEnabled(True)
                self.toolButton_main_back.setEnabled(True)

                # update the current window
                self.current_window = "main"

        return

    #----------------------------------------------#

    # function that writes the selector (for Settings)
    def writeSelectorIntoTxt(self):

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # write the selector
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_selector.txt"), "w") as f:
            f.write(str(self.current_selector))

        return

    #----------------------------------------------#

    # function that writes the device name into a txt file
    def writeDeviceIntoTxtForSubWindows(self, acc_name):

        # get accelerator specific devices
        acc_device_list = list(np.array(self.device_list)[np.array(self.acc_dev_list) == acc_name])

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # write the current device
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_device_premain.txt"), "w") as f:
            f.write(str(self.current_device))

        # write the current accelerator
        with open(os.path.join(self.app_temp_dir, "aux_txts", "current_accelerator_premain.txt"), "w") as f:
            f.write(str(acc_name))

        # write the exception of the current device
        with open(os.path.join(self.app_temp_dir, "aux_txts", "exception_premain.txt"), "w") as f:
            f.write("{}\n".format(self.exception_dict[str(self.current_device)]))

        # write the file: device_list_premain
        with open(os.path.join(self.app_temp_dir, "aux_txts", "device_list_premain.txt"), "w") as f:
            for dev in acc_device_list:
                f.write("{}\n".format(dev))

        # write the file: working_devices_premain
        with open(os.path.join(self.app_temp_dir, "aux_txts", "working_devices_premain.txt"), "w") as f:
            for dev in self.working_devices:
                f.write("{}\n".format(dev))

        # write the preloaded devices
        with open(os.path.join(self.app_temp_dir, "aux_txts", "preloaded_devices_premain.txt"), "w") as f:
            for dev in list(self.preloaded_devices):
                f.write("{}\n".format(dev))

        return

    #----------------------------------------------#

    # function that writes a file whenever the freeze button is pressed
    def sendFreezeText(self):

        # create the dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_txts")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_txts"))

        # if it is pressed
        if self.toolButton_freeze.isChecked():

            # write the file
            with open(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt"), "w") as f:
                f.write("True")

        # if it is not pressed
        else:

            # remove the freeze txt
            if os.path.exists(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt")):
                os.remove(os.path.join(self.app_temp_dir, "aux_txts", "freeze.txt"))

        return

    #----------------------------------------------#

    # function that writes the mode updates to an aux json file
    def sendUpdatesWorkingModes(self, modules_data, errors):

        # create the saving dir in case it does not exist
        if not os.path.exists(os.path.join(self.app_temp_dir, "aux_jsons")):
            os.mkdir(os.path.join(self.app_temp_dir, "aux_jsons"))

        # write the file: modules_data_for_preview_one_device
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "modules_data_for_preview_one_device.json"), "w") as fp:
            json.dump(modules_data, fp, sort_keys=True, indent=4)

        # write the file: errors_for_preview_one_device
        with open(os.path.join(self.app_temp_dir, "aux_jsons", "errors_for_preview_one_device.json"), "w") as fp:
            json.dump(errors, fp, sort_keys=True, indent=4)

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
            self.app.main_window.setWindowIcon(QIcon(SAVING_PATH + "/icons/diamond_2.png"))

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