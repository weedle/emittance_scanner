from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QMainWindow, QApplication
from PySide6.QtCore import QTimer, QRunnable, Slot, Signal, QObject, QThreadPool

import json
import sys
import time
import traceback
import os

import pysides
import numpy as np

# For development, a placeholder file is available that simulates a Galil microprocessor
#import motor_control_fake as mc
import motor_control_galil as mc
from pysides import object_map

# This is the main application
# You can modify this as needed, but be careful
# Running the motor past a limit switch can permanently damage the motor

# application in global values cause I was in a rush
running = True
keepCheckingStatus = True   
currentPosition = 0
currentStatus = 0
currentOutputVoltage = 0
currentInputVoltage = 0
PROPERTIES_FILE_NAME = "properties.json"
full_path = os.path.realpath(__file__)
script_path, _ = os.path.split(full_path)
properties_file_path = os.path.join(script_path, PROPERTIES_FILE_NAME)

# Static buttons
@Slot()
def goHome():
    mc.set_speed(200000)
    mc.move_to_position(pysides.auto_Home)
    mc.set_speed(50000)


@Slot()
def goFaraday():
    mc.set_speed(200000)
    mc.move_to_position(pysides.auto_Faraday)
    mc.set_speed(50000)

@Slot()
def goAbort():
    # send signal to stop running threads
    global currentOutputVoltage
    currentOutputVoltage = 0
    global running
    running = False

    # update UI
    pysides.object_map["lblAuto"].setStyleSheet("background-color: lightgrey")
    pysides.object_map["lblStart"].setStyleSheet("background-color: lightgrey")
    pysides.object_map["lblAuto"].setText("Initiate Auto Scan")
    pysides.object_map["lblStart"].setText("Initiate Custom Scan")

    # set output values to defaults
    mc.set_output_voltage(0)
    mc.set_speed(50000)
    mc.stop_motor()

def getMeasurementSettings():
    # get auto or user specified settings
    settings = {}
    settings["start"] = pysides.auto_Faraday
    settings["end"] = pysides.auto_End
    start_voltage = object_map["inputVoltageUserStart"].text()
    end_voltage = object_map["inputVoltageUserEnd"].text()
    voltage_steps = object_map["inputVoltageUserNumSteps"].text()
    start_motor = ""
    if object_map["inputMotorUserStart"].text() != "":
        start_motor = pysides.get_position_from_mm(object_map["inputMotorUserStart"].text())
    end_motor = ""
    if object_map["inputMotorUserEnd"].text() != "":
        end_motor = pysides.get_position_from_mm(object_map["inputMotorUserEnd"].text())
    motor_steps = ""
    if object_map["inputMotorUserNumSteps"].text() != "":
        motor_steps = object_map["inputMotorUserNumSteps"].text()

    settings["start_auto_voltage"] = float(object_map["inputVoltageAutoStart"].text())
    settings["end_auto_voltage"] = float(object_map["inputVoltageAutoEnd"].text())
    settings["voltage_auto_num_steps"] = int(object_map["inputVoltageAutoNumSteps"].text())
    settings["start_auto_motor"] = pysides.get_position_from_mm(int(object_map["inputMotorAutoStart"].text()))
    settings["end_auto_motor"] = pysides.get_position_from_mm(int(object_map["inputMotorAutoEnd"].text()))
    settings["motor_auto_num_steps"] = int(object_map["inputMotorAutoNumSteps"].text())
    try:
        settings["start_voltage"] = float(start_voltage) if start_voltage != "" else float(object_map["inputVoltageAutoStart"].text())
        settings["end_voltage"] = float(end_voltage) if end_voltage != "" else float(object_map["inputVoltageAutoEnd"].text())
        num_steps = int(voltage_steps) if voltage_steps != "" else int(object_map["inputVoltageAutoNumSteps"].text())
        settings["voltage_num_steps"] = num_steps

        settings["start_motor"] = int(start_motor) if start_motor != "" else pysides.get_position_from_mm(int(object_map["inputMotorAutoStart"].text()))
        settings["end_motor"] = int(end_motor) if end_motor != "" else pysides.get_position_from_mm(int(object_map["inputMotorAutoEnd"].text()))
        num_steps = int(motor_steps) if motor_steps != "" else int(object_map["inputMotorAutoNumSteps"].text())
        settings["motor_num_steps"] = num_steps
    except Exception as e:
        print("Failed to load user settings", e)

    return settings

def linkButtons(fnStart, fnAuto, fnCalibrate):
    pysides.object_map["btnHome"].clicked.connect(goHome)
    pysides.object_map["btnFaraday"].clicked.connect(goFaraday)
    pysides.object_map["btnAuto"].clicked.connect(fnAuto)
    pysides.object_map["btnStart"].clicked.connect(fnStart)
    pysides.object_map["btnCalibrate"].clicked.connect(fnCalibrate)
    pysides.object_map["btnAbort"].clicked.connect(goAbort)

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(int) #status
    progress = Signal(int, int, float) #position, status, input voltage


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        if self.signals.progress:
            self.kwargs['progress_callback'] = self.signals.progress

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit()
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))


class MainWindow(QMainWindow):
    position = 0
    status = 0
    voltage = 0
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        settings = self.loadSettings()
        mc.setup(settings["address"])
        pysides.file_path = settings["saveLocation"]


        self.setWindowTitle("IONSID Emittance Scanning")
        self.setCentralWidget(pysides.getMainFrame())
        linkButtons(self.startMeasurementWorker, self.startAutoMeasurementWorker, self.startCalibrationWorker)

        self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()
        
        self.doneCalibration()

    def loadSettings(self):
        print(properties_file_path)
        try:
            with open(properties_file_path) as file:
                data = json.load(file)
                print(data)
        except FileNotFoundError as e:
            print("Unable to find properties file")
            exit(1)
        return data

    def startAutoMeasurementWorker(self):
        worker = Worker(self.worker_auto_measurement)  # Any other args, kwargs are passed to the run function
        worker.signals.finished.connect(self.doneMeasurement)

        pysides.object_map["lblAuto"].setStyleSheet("background-color: orange")
        pysides.object_map["lblAuto"].setText("Running Auto Scan")

        # Execute
        self.threadpool.start(worker)

    def startMeasurementWorker(self):
        worker = Worker(self.worker_measurement)
        worker.signals.finished.connect(self.doneMeasurement)

        pysides.object_map["lblStart"].setStyleSheet("background-color: orange")
        pysides.object_map["lblStart"].setText("Running Custom Scan")
        
        # Execute
        self.threadpool.start(worker)

    def startCalibrationWorker(self):
        worker = Worker(self.worker_calibrate)
        worker.signals.finished.connect(self.doneCalibration)

        # Execute
        self.threadpool.start(worker)

    def doneMeasurement(self):
        global currentOutputVoltage
        currentOutputVoltage = 0
        global running
        running = False
        
        pysides.object_map["lblAuto"].setStyleSheet("background-color: lightgrey")
        pysides.object_map["lblStart"].setStyleSheet("background-color: lightgrey")
        pysides.object_map["lblAuto"].setText("Initiate Auto Scan")
        pysides.object_map["lblStart"].setText("Initiate Custom Scan")
        
        pysides.runFile()
        print("MEASUREMENT COMPLETE")
        
        mc.set_speed(200000)
        mc.set_output_voltage(0)
        mc.move_to_position(pysides.auto_Faraday)
        mc.set_speed(50000)

    # get current state from Galil, let main thread know so we can update UI
    def worker_update(self, progress_callback):
        global keepCheckingStatus
        keepCheckingStatus = True
        while keepCheckingStatus:
            # position, status, input voltage
            position = mc.get_position()
            status = mc.check_status()
            voltage = mc.get_analog_input()
            try:
                progress_callback.emit(position, status, voltage)
            except RuntimeError:
                return
            time.sleep(0.1)
        keepCheckingStatus = False

    # check each voltage at each position step using the given ranges and step sizes
    def do_measurement(self, startMotor, endMotor, stepsMotor,
                       startVoltage, endVoltage, stepsVoltage):
        global running
        running = True
        global currentOutputVoltage
        global currentPosition

        while running:
            try:
                pysides.setFileName()
                datafile = open(os.path.join(pysides.file_path, object_map["inputFile"].text()), 'w')
                print(object_map["inputFile"].text())

                datafile.write(object_map["inputComment"].text() + "\n")
                # Plate Length and Plate Gap (fixed)
                datafile.write("40.78 4\n")
                # Beam Energy
                datafile.write(object_map["inputEnergy"].text() + "\n")
                # Motor Start in mm
                datafile.write(str(pysides.get_position_in_mm_raw(startMotor)) + "\n")
                steps_to_mm = 196 / (pysides.auto_End - pysides.auto_Home)
                print("steps to mm conversion is", steps_to_mm)
                datafile.write(str(round(stepsMotor * steps_to_mm, 4)) + "\n")
                datafile.write(str(startVoltage) + "\n")
                datafile.write(str(round(endVoltage - startVoltage / stepsVoltage, 4)) + "\n")
                datafile.write(str(stepsVoltage) + "\n")
                datafile.write(str(stepsMotor) + "\n")
                
                mc.set_speed(200000)

                for pos in np.linspace(startMotor, endMotor, stepsMotor):
                    if not running:
                        return
                    time.sleep(1)
                    mc.move_to_position(pos)
                    while mc.is_in_motion() and running:
                        print(f"curr pos {currentPosition} ({pysides.get_position_in_mm(currentPosition)}), aiming for pos {pos} ({pysides.get_position_in_mm(pos)})")
                        time.sleep(0.5)
                    dataline = ""
                    for currentOutputVoltage in np.linspace(startVoltage, endVoltage, stepsVoltage):
                        if not running:
                            return
                        mc.set_output_voltage(round(currentOutputVoltage, 2))
                        time.sleep(0.05)
                        dataline += str(currentInputVoltage) + " "
                        print(f"currently at {pos} and sending out {round(currentOutputVoltage, 2)} to read in {currentInputVoltage}")
                    datafile.write(dataline + "\n")
                datafile.close()
                running = False
            except RuntimeError as e:
                print("Failed to execute measurement", e)
                running = False
                return
            time.sleep(0.1)
            
    def worker_calibrate(self, progress_callback):
        global running
        running = True
        if (mc.check_forward_switch() or 
            mc.check_home_switch() or 
            mc.check_reverse_switch()):
                print("already at limit switch")
        else:
            mc.find_edge()
            inMotion = mc.is_in_motion()
            
            while inMotion:
                inMotion = mc.is_in_motion()
                time.sleep(0.1)
        
        running = False
            
    def doneCalibration(self):
        global running
        running = False

        if mc.check_reverse_switch():
            pysides.auto_Home = mc.get_position()
            pysides.auto_Faraday = pysides.auto_Home + 3679098
            pysides.auto_End = pysides.auto_Faraday + 2578395
            print("At reverse switch!")
            pysides.calibrated = True 
        
        if mc.check_home_switch():
            print("At home switch!")
            pysides.auto_Faraday = mc.get_position()
            pysides.auto_End = pysides.auto_Faraday + 2578395
            pysides.auto_Home = pysides.auto_Faraday - 3679098
            pysides.calibrated = True 
        
        if mc.check_forward_switch():
            pysides.auto_End = mc.get_position()
            pysides.auto_Faraday = pysides.auto_End - 2578395
            pysides.auto_Home = pysides.auto_Faraday - 3679098
            print("At forward switch!")
            pysides.calibrated = True 
            
        pysides.object_map["btnHome"].setEnabled(pysides.calibrated)
        pysides.object_map["btnFaraday"].setEnabled(pysides.calibrated)
        pysides.object_map["btnAuto"].setEnabled(pysides.calibrated)
        pysides.object_map["btnStart"].setEnabled(pysides.calibrated)
        
        pysides.setup_default_values()

    # retrieve settings and kick off measurement with default settings
    def worker_auto_measurement(self, progress_callback):
        settings = getMeasurementSettings()
        startVoltage = settings["start_auto_voltage"]
        endVoltage = settings["end_auto_voltage"]
        stepsVoltage = settings["voltage_auto_num_steps"]
        startMotor = settings["start_auto_motor"]
        endMotor = settings["end_auto_motor"]
        stepsMotor = settings["motor_auto_num_steps"]
        self.do_measurement(startMotor, endMotor, stepsMotor,
                       startVoltage, endVoltage, stepsVoltage)

    # retrieve settings and kick off measurement with custom settings
    def worker_measurement(self, progress_callback):
        settings = getMeasurementSettings()
        startVoltage = settings["start_voltage"]
        endVoltage = settings["end_voltage"]
        stepsVoltage = settings["voltage_num_steps"]
        startMotor = settings["start_motor"]
        endMotor = settings["end_motor"]
        stepsMotor = settings["motor_num_steps"]
        self.do_measurement(startMotor, endMotor, stepsMotor,
                       startVoltage, endVoltage, stepsVoltage)

    # A lot of these printouts are for debugging
    # Feel free to remove them or otherwise modify this file as needed
    def print_output(self, position, status, inputVoltage):
        print("reading current position as", position, "status is", status)
        if mc.check_forward_switch():
            print("at forward switch")
        if mc.check_reverse_switch():
            print("at reverse switch")
        if mc.check_home_switch():
            print("at home switch")

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def recurring_timer(self):
        global currentOutputVoltage
        global currentPosition
        global currentStatus
        global currentInputVoltage
        position = mc.get_position()
        status = mc.check_status()
        voltage = mc.get_analog_input()
        
        currentPosition = position
        currentStatus = status
        currentInputVoltage = voltage
        
        pysides.updateStatus(position, status, currentOutputVoltage, currentInputVoltage)
        # Note - Reverse Limit, Home, and Forward for the Galil correspond to
        # Home, Faraday, and End in our program, respectively
        # Also we changed Home to Park at the last minute
        # I'm only changing that in the UI side to avoid breaking anything
        pysides.updateLimitSwitchStates(
            mc.check_reverse_switch(),
            mc.check_home_switch(),
            mc.check_forward_switch()
        )

        return 1

    # Send stop signal to threads, clean up
    def closeEvent(self, event):
        global running
        running = False
        global keepCheckingStatus
        keepCheckingStatus = False
        self.threadpool.waitForDone(1000)
        time.sleep(0.5)
        mc.cleanup()
        time.sleep(0.5)


app = QApplication(sys.argv)
window = MainWindow()
app.exec()
