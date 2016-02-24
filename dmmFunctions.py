import serial
import glob #used for finding all the pathnames matching a specified pattern
import time

global dmmCom
global dmmComIsOpen

def SetupComport(tempDevice):
    global dmmCom
    global dmmComIsOpen
    dmmComIsOpen = False
    dmmCom = serial.Serial(tempDevice, baudrate=9600, timeout=3)
    if dmmCom.isOpen():
        if AssignComport(dmmCom):
            dmmComIsOpen = True
        else:
            dmmCom.close()
    if dmmComIsOpen:
        return 1
    else:
        return 0

#Called from the setupDmmComport() function
def AssignComport(device):                            
    device.write('*IDN?\n')
    tempString = device.readline()
    if '34401A' in tempString:
        device.write('system:remote\n')
        return 1                                    
    return 0

#default function params 'def' allows dmm to automatically select the correct range
#to request a resistance measurement, set measurementType to 'res' 
def Measure(measurementType='volt:dc', dmmRange='def', dmmResolution='def'):
        reply = ''
        error = ''
        dmmCom.write('meas:' + measurementType + '? ' + dmmRange + ", " + dmmResolution + '\n')
        queryTime = time.time()
        reply = dmmCom.readline()    
        queryTime = time.time() - queryTime
        if not TimeoutCheck(queryTime, 'DmmMeasure()'):
            dmmCom.write('system:error?\n')
            error = dmmCom.readline()
            raise ValueError('dmm timeout')
        dmmCom.write('system:error?\n')
        error = dmmCom.readline()
        if 'No error' in error:
            return reply
        else:
            raise ValueError('dmm error')

def TimeoutCheck(queryTime, taskName):
    #if read op. > 3 sec, generate prog. error
    if queryTime >= 3:
        return 0
    else:
        return 1
