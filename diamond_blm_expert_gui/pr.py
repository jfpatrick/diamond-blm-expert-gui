# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_dialog_auto.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(600, 800)
        Form.setStyleSheet("")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout_2.setContentsMargins(6, 20, 6, 6)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.frame_properties = QtWidgets.QFrame(Form)
        self.frame_properties.setStyleSheet("")
        self.frame_properties.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_properties.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_properties.setObjectName("frame_properties")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.frame_properties)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.scrollArea_properties = QtWidgets.QScrollArea(self.frame_properties)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_properties.sizePolicy().hasHeightForWidth())
        self.scrollArea_properties.setSizePolicy(sizePolicy)
        self.scrollArea_properties.setStyleSheet("QScrollArea{\n"
"    margin-left: 50px;\n"
"    margin-right: 50px;\n"
"    background-color: rgb(227, 227, 227);\n"
"}\n"
"\n"
"QScrollBar:vertical{\n"
"     background-color: white;\n"
" }\n"
"\n"
"CCommandButton{\n"
"    background-color: rgb(255, 255, 255);\n"
"    border: 1px solid black;\n"
"}\n"
"\n"
"CCommandButton:hover{\n"
"    background-color: rgb(230, 230, 230);\n"
"}\n"
"\n"
"CCommandButton:pressed{\n"
"    background-color: rgb(200, 200, 200);\n"
"}")
        self.scrollArea_properties.setFrameShadow(QtWidgets.QFrame.Plain)
        self.scrollArea_properties.setLineWidth(1)
        self.scrollArea_properties.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea_properties.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea_properties.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.scrollArea_properties.setWidgetResizable(True)
        self.scrollArea_properties.setAlignment(QtCore.Qt.AlignCenter)
        self.scrollArea_properties.setObjectName("scrollArea_properties")
        self.scrollingContents_properties = QtWidgets.QWidget()
        self.scrollingContents_properties.setGeometry(QtCore.QRect(0, 50, 454, 575))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollingContents_properties.sizePolicy().hasHeightForWidth())
        self.scrollingContents_properties.setSizePolicy(sizePolicy)
        self.scrollingContents_properties.setStyleSheet("QLabel{\n"
"    border: 1px solid black;\n"
"    background-color: rgb(236, 236, 236);\n"
"}\n"
"\n"
"CLabel{\n"
"    border: 1px solid black;\n"
"    background-color: rgb(236, 236, 236);\n"
"}\n"
"\n"
"QGroupBox{\n"
"    background-color: rgb(232, 232, 232);\n"
"}")
        self.scrollingContents_properties.setObjectName("scrollingContents_properties")
        self.verticalLayout_scrollingContents_properties = QtWidgets.QVBoxLayout(self.scrollingContents_properties)
        self.verticalLayout_scrollingContents_properties.setObjectName("verticalLayout_scrollingContents_properties")
        self.scrollArea_properties.setWidget(self.scrollingContents_properties)
        self.verticalLayout_6.addWidget(self.scrollArea_properties)
        self.verticalLayout_2.addWidget(self.frame_properties)
        self.frame_get_set = QtWidgets.QFrame(Form)
        self.frame_get_set.setStyleSheet("")
        self.frame_get_set.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_get_set.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame_get_set.setObjectName("frame_get_set")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame_get_set)
        self.horizontalLayout.setContentsMargins(9, 0, 9, -1)
        self.horizontalLayout.setSpacing(16)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.scrollArea_get_set = QtWidgets.QScrollArea(self.frame_get_set)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_get_set.sizePolicy().hasHeightForWidth())
        self.scrollArea_get_set.setSizePolicy(sizePolicy)
        self.scrollArea_get_set.setStyleSheet("background-color: transparent;")
        self.scrollArea_get_set.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_get_set.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea_get_set.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea_get_set.setWidgetResizable(True)
        self.scrollArea_get_set.setAlignment(QtCore.Qt.AlignCenter)
        self.scrollArea_get_set.setObjectName("scrollArea_get_set")
        self.scrollingContents_get_set = QtWidgets.QWidget()
        self.scrollingContents_get_set.setGeometry(QtCore.QRect(0, 0, 556, 68))
        self.scrollingContents_get_set.setObjectName("scrollingContents_get_set")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.scrollingContents_get_set)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.pushButton_get = QtWidgets.QPushButton(self.scrollingContents_get_set)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_get.sizePolicy().hasHeightForWidth())
        self.pushButton_get.setSizePolicy(sizePolicy)
        self.pushButton_get.setMinimumSize(QtCore.QSize(100, 32))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_get.setFont(font)
        self.pushButton_get.setStyleSheet("QPushButton{\n"
"    background-color: rgb(255, 255, 255);\n"
"    border: 2px solid #A6A6A6;\n"
"}\n"
"\n"
"QPushButton:hover{\n"
"    background-color: rgb(230, 230, 230);\n"
"}\n"
"\n"
"QPushButton:pressed{\n"
"    background-color: rgb(200, 200, 200);\n"
"}")
        self.pushButton_get.setObjectName("pushButton_get")
        self.horizontalLayout_2.addWidget(self.pushButton_get)
        self.pushButton_set = QtWidgets.QPushButton(self.scrollingContents_get_set)
        self.pushButton_set.setMinimumSize(QtCore.QSize(100, 32))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_set.setFont(font)
        self.pushButton_set.setStyleSheet("QPushButton{\n"
"    background-color: rgb(255, 255, 255);\n"
"    border: 2px solid #A6A6A6;\n"
"}\n"
"\n"
"QPushButton:hover{\n"
"    background-color: rgb(230, 230, 230);\n"
"}\n"
"\n"
"QPushButton:pressed{\n"
"    background-color: rgb(200, 200, 200);\n"
"}")
        self.pushButton_set.setObjectName("pushButton_set")
        self.horizontalLayout_2.addWidget(self.pushButton_set)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.scrollArea_get_set.setWidget(self.scrollingContents_get_set)
        self.horizontalLayout.addWidget(self.scrollArea_get_set)
        self.verticalLayout_2.addWidget(self.frame_get_set)
        self.verticalLayout_2.setStretch(0, 95)
        self.verticalLayout_2.setStretch(1, 5)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.pushButton_get.setText(_translate("Form", "GET"))
        self.pushButton_set.setText(_translate("Form", "SET"))
