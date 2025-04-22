from ast import Try
from re import S
import gclib
import time

galil_connector = gclib.py()

def setup():
    galil_connector.GOpen('192.1.42.2')
    print(galil_connector.GInfo())
    galil_connector.GCommand('CN1,-1,1')
    galil_connector.GCommand('SP10000;AC10000;DC10000')

def find_edge():
    galil_connector.GCommand('SP10000')
    galil_connector.GCommand('FE;BG;')
    time.sleep(0.1)

def check_status():
    status_word = 0
    try:
        status_word = int(galil_connector.GCommand('TS'))
    except Exception as e:
        print(e)
        return -1
    return status_word

def is_in_motion():
    return check_status() & 128
    
def check_home_switch():
    if(check_status() & 2):
        return True
    return False

def check_reverse_switch():
    if(check_status() & 4):
        return False
    return True

def check_forward_switch():
    if(check_status() & 8):
        return False
    return True

def check_in_motion(status_word):
    if(status_word & 128):
        return True
    return False

def get_position():
    return int(galil_connector.GCommand('RP'))

def get_analog_input():
    return float(galil_connector.GCommand('MG @AN[1]'))

def set_output_voltage(voltage):
    galil_connector.GCommand('AO2,' + str(voltage))

def move_to_position(position):
    galil_connector.GCommand('PA' + str(position))
    galil_connector.GCommand('BG')

def set_speed(velocity):
    galil_connector.GCommand('SP' + str(velocity))

def stop_motor():
    # stop the motor
    galil_connector.GCommand('ST;AB;')
    
def cleanup():
    stop_motor()
    set_speed(100000)
    set_output_voltage(0)

setup()
