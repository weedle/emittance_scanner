import sys
import time

from os import listdir

from PySide6.QtCore import Qt, QMargins, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout
)

import do_contour

#windows
#file_path = "C:\\Users\\IONSIDES11PC\\OneDrive\\Desktop\\emittance_scanner\\emittance\\"
#mac
file_path = r"C:\Users\IONSIDES11PC\OneDrive\Documents\emittance_scanner\results"

# UI file
# This can be modified to change the user interface as needed

object_map = dict()

auto_Home = -1
auto_Faraday = -1
auto_End = -1

calibrated = False

voltage_Start = -2
voltage_End = 2

motor_steps = 100
voltage_steps = 50

STATUS_HOME = 1
STATUS_FARADAY = 2
STATUS_END = 3

def getButton(name, label):
    button = QPushButton(label)
    object_map[name] = button
    return button

def getQFrame():
    frame = QFrame()
    frame.setFrameStyle(QFrame.NoFrame)
    #frame.setContentsMargins(QMargins(0, 0, 0, 0))
    return frame

def getAbortFrame():
    frame = getQFrame()
    pane = QVBoxLayout()
    frame.setLayout(pane)

    button = getButton("btnAbort", "ABORT")
    button.setFixedWidth(200)

    pane.addWidget(button)

    lbl1 = QLabel("Current Position: -")
    lbl2 = QLabel("Current Voltage Output: -")
    lbl3 = QLabel("Current Voltage Reading: -")

    object_map["statusPosition"] = lbl1
    object_map["statusVoltageOutput"] = lbl2
    object_map["statusVoltageInput"] = lbl3

    pane.addWidget(lbl1)
    pane.addWidget(lbl2)
    pane.addWidget(lbl3)

    return frame

def generateButtonFrame():
    button_frame = getQFrame()
    button_pane = QHBoxLayout()
    button_pane.setSpacing(0)
    button_frame.setLayout(button_pane)
    for params in [
        ["Home", "HOME", "Go to HOME Position"],
        ["Faraday", "FARADAY CUP", "Go to Faraday Cup Position"],
        ["Auto", "AUTO SCAN", "Initiate Auto Scan"],
        ["Start", "START SCAN", "Initiate Custom Scan"],
        ["Calibrate", "CALIBRATE", "Recalibrate Switch Positions"]]:
        frame = getQFrame()
        pane = QVBoxLayout()
        frame.setLayout(pane)

        button = getButton("btn" + params[0], params[1])
        button.setFixedWidth(200)

        pane.addWidget(button)

        label = QLabel(params[2])
        label.setFixedWidth(button.width())
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: lightgrey")
        
        object_map["lbl" + params[0]] = label

        pane.addWidget(label)
        button_pane.addWidget(frame)

    button_pane.addWidget(getAbortFrame())        

    return button_frame

def generateLabelAndInputBoxFrame(lbl):
    frame = getQFrame()
    pane = QVBoxLayout()
    pane.setSpacing(0)
    pane.setContentsMargins(QMargins(0, 0, 0, 0))
    frame.setLayout(pane)

    pane.addWidget(QLabel(lbl))
    pane.addWidget(QLineEdit())

    return frame

def generateLabelAndWidgetFrame(lbl, widget):
    frame = getQFrame()
    pane = QVBoxLayout()
    #pane.setSpacing(0)
    frame.setLayout(pane)

    label = QLabel(lbl)
    label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

    pane.addWidget(label)
    pane.addWidget(widget)

    return frame

def getLineEdit():
    textbox = QLineEdit()
    textbox.setAlignment(Qt.AlignmentFlag.AlignRight)
    return textbox

def generateCustomPane(lbl, moltage):
    custom_frame = getQFrame()
    custom_frame.setFrameStyle(QFrame.StyledPanel)
    #custom_frame.setFixedHeight(150)
    custom_pane = QVBoxLayout()
    custom_pane.setSpacing(0)
    custom_pane.setContentsMargins(QMargins(0, 0, 0, 0))
    #custom_pane.setContentsMargins(QMargins(0, 0, 0, 0))
    custom_frame.setLayout(custom_pane)
    #custom_frame.setContentsMargins(QMargins(0, 0, 0, 0))

    input_frame = getQFrame()
    input_pane = QHBoxLayout()
    input_pane.setSpacing(0)
    input_pane.setContentsMargins(QMargins(0, 0, 0, 0))
    input_frame.setLayout(input_pane)


    inputAuto = getLineEdit()
    inputAuto.setReadOnly(True)
    inputUser = getLineEdit()

    object_map["input" + moltage + "Auto" + lbl] = inputAuto
    object_map["input" + moltage + "User" + lbl] = inputUser

    input_pane.addWidget(generateLabelAndWidgetFrame("Auto Setting", inputAuto))
    input_pane.addWidget(generateLabelAndWidgetFrame("User Setting", inputUser))

    if lbl == "NumSteps":
        lbl = "# Steps"
    label = QLabel(lbl)
    label.setStyleSheet("font-size: 16pt")
    label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
    custom_pane.addWidget(label)
    custom_pane.addWidget(input_frame)
    return custom_frame

def generateMotorOrVoltageFrame(moltage):
    motor_frame = getQFrame()
    motor_pane = QHBoxLayout()
    motor_pane.setSpacing(0)
    motor_frame.setLayout(motor_pane)

    motor_pane.addWidget(QLabel(moltage))

    motor_pane.addWidget(generateCustomPane("Start", moltage))
    motor_pane.addWidget(generateCustomPane("End", moltage))
    motor_pane.addWidget(generateCustomPane("NumSteps", moltage))

    return motor_frame

def generateCommentRow():
    comment_frame = getQFrame()
    comment_pane = QHBoxLayout()
    comment_frame.setLayout(comment_pane)

    commentBox = QLineEdit()
    object_map["inputComment"] = commentBox
    commentBox.setText("Emittance Data for Source")

    comment_pane.addWidget(QLabel("Comment Line:"))
    comment_pane.addWidget(commentBox)

    return comment_frame

def generateEnergyRow():
    energy_frame = getQFrame()
    energy_pane = QHBoxLayout()
    energy_frame.setLayout(energy_pane)

    energyBox = QLineEdit()
    object_map["inputEnergy"] = energyBox
    energyBox.setText("25000")

    energy_pane.addWidget(QLabel("Beam Energy (V):"))
    energy_pane.addWidget(energyBox)

    return energy_frame

def generateContourPlot():
    print("generating contour with data file", object_map["inputFile"].text())
    do_contour.load_file(file_path + object_map["inputFile"].text())
    do_contour.run()
    
def setFileName():
    object_map["inputFile"].setText("datafile_" + time.strftime("%Y-%m-%d_%H-%M") + ".dat")

def generateFileRow(lbl):
    comment_frame = getQFrame()
    comment_pane = QHBoxLayout()
    comment_frame.setLayout(comment_pane)

    fileBox = QLineEdit()
    object_map["inputFile"] = fileBox
    setFileName()

    comment_pane.addWidget(QLabel(lbl))
    comment_pane.addWidget(fileBox)

    runButton = getButton("btnRunSavedFile", "Run")
    runButton.clicked.connect(generateContourPlot)

    comment_pane.addWidget(runButton)

    return comment_frame

def populateListOfFiles():
    comboBox = object_map["comboBoxFiles"]
    files = listdir(file_path)
    for file in files:
        if file[-4:] == ".dat":
            comboBox.addItem(file)

def generateSavedFilesRow():
    comment_frame = getQFrame()
    comment_pane = QHBoxLayout()
    comment_pane.setStretch(0, 0)
    comment_pane.setSpacing(0)
    comment_pane.setAlignment(Qt.AlignmentFlag.AlignLeft)
    comment_frame.setLayout(comment_pane)

    comment_pane.addWidget(QLabel("Saved Files:"))

    object_map["comboBoxFiles"] = QComboBox()
    populateListOfFiles()

    comment_pane.addWidget(object_map["comboBoxFiles"])
    runButton = getButton("btnRunSavedFile", "Run")
    runButton.clicked.connect(runFileFromList)

    comment_pane.addWidget(runButton)

    return comment_frame

def getMainFrame():
    mainFrame = getQFrame()
    layout = QVBoxLayout(mainFrame)
    layout.setSpacing(0)

    layout.addWidget(generateButtonFrame())
    layout.addWidget(generateMotorOrVoltageFrame("Motor"))
    layout.addWidget(generateMotorOrVoltageFrame("Voltage"))
    layout.addWidget(generateCommentRow())
    layout.addWidget(generateEnergyRow())
    layout.addWidget(generateFileRow("File name"))
    #layout.addWidget(generateFileRow("Timestamp file name"))
    layout.addWidget(generateSavedFilesRow())

    setup_default_values()

    return mainFrame

def setup_default_values():
    object_map["inputMotorAutoStart"].setText("160")
    object_map["inputMotorAutoEnd"].setText("196")
    object_map["inputVoltageAutoStart"].setText(str(voltage_Start))
    object_map["inputVoltageAutoEnd"].setText(str(voltage_End))
    object_map["inputMotorAutoNumSteps"].setText(str(motor_steps))
    object_map["inputVoltageAutoNumSteps"].setText(str(voltage_steps))

def get_position_in_mm_raw(position):
    if auto_End == auto_Home:
        return f"UNCALIBRATED"
    total_distance_in_steps = auto_End - auto_Home
    percentage_travelled = (position - auto_Home) / total_distance_in_steps
    return round(percentage_travelled * 193, 2)

def get_position_in_mm(position):
    convertedPos = get_position_in_mm_raw(position)
    if convertedPos != "UNCALIBRATED":
        return f"{get_position_in_mm_raw(position) }mm"
    return convertedPos
    
def get_position_from_mm(mm):
    total_distance_in_steps = auto_End - auto_Home
    return int((float(mm) / 193) * total_distance_in_steps + auto_Home)

# Note: adding status here is useful if something goes wrong, but I'm removing it for release
def updateStatus(position, status, voltageOutput, voltageInput):
    object_map["statusPosition"].setText(f"Current Position: {get_position_in_mm(position)}")
    object_map["statusVoltageOutput"].setText("Current Voltage Output: " + str(round(voltageOutput, 2)))
    object_map["statusVoltageInput"].setText("Current Voltage Reading: " + str(round(voltageInput, 2)))

# Initially we had a button to move to the End position
# but we removed it cause we couldn't think of why that would be useful
def updateLimitSwitchStates(atHome, atFaraday, atEnd):
    active = "background-color: green"
    inactive = "background-color: lightgrey"
    notCalibrated = "background-color: grey"
    if calibrated:
        if atHome:
            object_map["lblHome"].setStyleSheet(active)
            object_map["lblHome"].setText("At Park")
        else:
            object_map["lblHome"].setStyleSheet(inactive)
            object_map["lblHome"].setText("Park")

        if atFaraday:
            object_map["lblFaraday"].setStyleSheet(active)
            object_map["lblFaraday"].setText("At Faraday Cup")
        else:
            object_map["lblFaraday"].setStyleSheet(inactive)
            object_map["lblFaraday"].setText("Faraday Cup")
    else:
            object_map["lblHome"].setStyleSheet(notCalibrated)
            object_map["lblFaraday"].setStyleSheet(notCalibrated)
            object_map["lblHome"].setText("Park")
            object_map["lblFaraday"].setText("Faraday Cup")

@Slot()
def runFile():
    do_contour.load_file(file_path + object_map["inputFile"].text())
    do_contour.run()

@Slot()
def runFileFromList():
    comboBox = object_map["comboBoxFiles"]
    do_contour.load_file(file_path + comboBox.currentText())
    do_contour.run()
