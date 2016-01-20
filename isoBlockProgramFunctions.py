import time
import serial
import glob #finds all the pathnames matching a specified pattern
from smbus import SMBus #library for I2C communication
import numpy as np
import Tkinter
import sys
import RPi.GPIO as GPIO
import numpy as np

global dmmCom
global dmmComIsOpen
global eLoadCom
global eLoadComIsOpen
global pSupplyCom
global pSupplyComIsOpen
global comportList

syncNotEnable = 8
isoBlockEnable = 10
rPiReset = 12
vinShuntEnable = 16
vinKelvinEnable = 18
voutShuntEnable = 22
voutKelvinEnable = 24
fanEnable = 26
picEnable = 32

GPIO.setwarnings(False) #Disable the warning related to GPIO.setup command: "RuntimeWarning: This channel is already in use, continuing anyway."
GPIO.setmode(GPIO.BOARD) #Refer to RPi header pin# instead of Broadcom pin#

GPIO.setup(syncNotEnable, GPIO.OUT)
GPIO.output(syncNotEnable, 1) # 1=disable so I2C address=0x1E  or else 0=enable, I2C address=0x1F
GPIO.setup(isoBlockEnable, GPIO.OUT)
GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
GPIO.setup(vinShuntEnable, GPIO.OUT)
GPIO.output(vinShuntEnable, 0) # 0=disable
GPIO.setup(vinKelvinEnable, GPIO.OUT)
GPIO.output(vinKelvinEnable, 0) # 0=disable
GPIO.setup(voutShuntEnable, GPIO.OUT)
GPIO.output(voutShuntEnable, 0) # 0=disable
GPIO.setup(voutKelvinEnable, GPIO.OUT)
GPIO.output(voutKelvinEnable, 0) # 0=disable
GPIO.setup(fanEnable, GPIO.OUT)
GPIO.output(fanEnable, 0) # 0=disable
GPIO.setup(picEnable, GPIO.OUT)
GPIO.output(picEnable, 0) # 0=disable
GPIO.setup(rPiReset, GPIO.OUT)
GPIO.output(rPiReset, 1) # 0=enable

#i2c globals
ADDR = 0x04 #Slave address (Arduino Leonardo)
#RPi has 2 I2C buses, specify which one
bus = SMBus(1)

mainWindow = Tkinter.Tk()

dmmComIsOpen = False
eLoadComIsOpen = False
pSupplyComIsOpen = False
comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices

testDataList = ['Test Results:']
testErrorList = ['Test Errors:']

#************************************************************************************
#Functions
#************************************************************************************

def MainWindow():    
    StartButton = Tkinter.Button(mainWindow, text='Start Test', command=Main)
    StartButton.pack()
    QuitButton = Tkinter.Button(mainWindow, text='Quit', command=QuitTest)
    QuitButton.pack()
    mainWindow.mainloop()

def Main():
    print 'MainRoutine'
    #Get the current system date and time
    datetime = time.strftime('%m/%d/%Y %H:%M:%S')

    #dmmThread = threading.Thread(name='dmmThread', target=Func.DmmMeasure, args=(15,))
    I2CWrite(0x00)
    I2CRead(6)

    try:
        temp = ''
        temp = DmmMeasure()
        print('DMM measurement: ' + temp)
        if not VoutCalibration(10):
            print 'Failed VoutCalibration'
            FailRoutine()
            
        GPIO.output(syncNotEnable, 0)
        #time.sleep(1)
        GPIO.output(syncNotEnable, 1)

        #When everythin passes:
        #Send pass record to database
        #make something on the GUI turn green
        for index in range(len(testErrorList)):
            print testErrorList[index]
        for index in range(len(testDataList)):
            print testDataList[index]
        return
    
    except ValueError, err:
        print 'exception response in main program: '
        print err
        for index in range(len(testErrorList)):
            print testErrorList[index]
        for index in range(len(testDataList)):
            print testDataList[index]
        CloseProgram()
        mainWindow.destroy()


def QuitTest():
    mainWindow.destroy()
    
#***************************************************************************
#Test Equipment setup
#***************************************************************************
def SetupComports():
    if len(comportList) > 0:
        if not AssignDMMComport(comportList):
            print 'unable to communicate with dmm'
            return 0
        if not AssignEloadComport(comportList):
            print 'unable to communicate with Eload'
            return 0
        if not AssignPsupplyComport(comportList):
            print 'unable to communicate with Psupply'
            return 0
        return 1
    else:
        #unable to find any attached devices
        return 0

def CloseComports():
    if dmmComIsOpen:
        if dmmCom.isOpen():
            dmmCom.close()
    if eLoadComIsOpen:
        if eLoadCom.isOpen():
            eLoadCom.close()
    if pSupplyComIsOpen:
        if pSupplyCom.isOpen():
            pSupplyCom.close()
    return

#Called from the SetupComports() function
def AssignDMMComport(comportList):
    global dmmCom
    global dmmComIsOpen
    for index in range(len(comportList)):
        try:
            tempDevice = serial.Serial(comportList[index], baudrate=9600, timeout=3)
        except:
            print 'Exception occurred while setting up comport: ' + tempDevice + ' in the "AssignDMMComport" function'
        else:            
            if tempDevice.isOpen():                
                tempDevice.write('*IDN?\n')
                tempString = tempDevice.readline()
                if '34401A' in tempString:
                    comportList.remove(comportList[index])#remove device from List
                    dmmComIsOpen = True
                    dmmCom = tempDevice
                    dmmCom.write('system:remote\n')
                    dmmCom.readline()
                    return 1
                else:
                    #continue loop if system info didn't return correct
                    tempDevice.close()
            else:
                print 'Unable to open comport: ' + comportList[index]
    return 0
                
#Called from the SetupComports() function
def AssignEloadComport(deviceList):
    return 1

#Called from the SetupComports() function
def AssignPsupplyComport(deviceList):
    return 1

#***************************************************************************
#DMM task functions
#***************************************************************************

#default function params 'def' allows dmm to automatically select the correct range
def DmmMeasure(measurementType='volt', dmmRange='def', dmmResolution='def'):
    reply = ''
    error = ''
    dmmCom.write('meas:' + measurementType + ':dc? ' + dmmRange + ", " + dmmResolution + '\n')
    queryTime = time.time()
    reply = dmmCom.readline()    
    queryTime = time.time() - queryTime
    if not DmmTimeoutCheck(queryTime, 'DmmMeasure()'):
        dmmCom.write('system:error?\n')
        error = dmmCom.readline()
        testErrorList.append(error)
        raise ValueError('dmm timeout')
    dmmCom.write('system:error?\n')
    error = dmmCom.readline()
    if 'No error' in error:
        return reply
    else:
        testErrorList.append('dmm error : ' + error)
        raise ValueError('dmm error')

def DmmTimeoutCheck(queryTime, taskName):
    #if read op. > 3 sec, generate prog. error
    if queryTime >= 3:
        return 0
    else:
        return 1
#***************************************************************************
#Programming PIC
#***************************************************************************
def ProgramPic():
    print("ProgramPic function")
    #
    #
    return

def FailRoutine():
    for index in range(len(testDataList)):
        print testDataList[index]
    for index in range(len(testErrorList)):
        print testErrorList[index]
    TestResultToDatabase('fail')
    return

def EloadCommand():
    print("EloadCommand function")
    #
    #
    return

def EloadQuery():
    print("EloadQuery function")
    #
    #
    return

def PSupplyCommand():
    print("PSupplyCommand function")
    #send serial command to PS
    #
    #return errors or other information
    return

def PSupplyQuery():
    print("PowerSupplyQuery function")
    #send serial command to PS
    #
    #return current draw or other information
    return
    
def TestResultToDatabase(result):
    #
    #
    return

def I2CWrite(message):
    print("write to Arduino register:")
    #bus.write_i2c_block_data(ADDR, message)
    bus.write_byte(ADDR, message)
    #if message write/read fails:
        #testErrorList.append('error in VoutCalibration(), variable "sign" = ' + sign)
        #return 0
    return 1

def I2CRead(message):
    print 'read Arduino register:'
    calRoutineCmd = bus.read_i2c_block_data(ADDR, 189, message)
    print(calRoutineCmd)
    print(np.asarray(calRoutineCmd))
    #if message write/read fails:
        #testErrorList.append('error in VoutCalibration(), variable "sign" = ' + sign)
        #return 0
    return 1

def VoutCalibration(vout):
    vout = float(vout)
    vOffsetCoarse = 0
    vOffsetFine = 0
    sign = -1
    if vout < 10.0:
        sign = 0
    elif vout >= 10.0:
        sign = 1
    else:
        testErrorList.append('error in VoutCalibration(), variable "sign" = ' + str(sign))
        return 0
    testDataList.append('sign,' + str(sign))
    vOffsetCoarse = (abs(10.0-vout)*0.09823)/(0.0158) #unit=bit
    testDataList.append('vOffsetCoarse,' + str(vOffsetCoarse))
    vOffsetFine = (128*sign)+int(((abs(10.0-vout)*0.09823)-(vOffsetCoarse*0.0158))/(0.0008))#unit=bit
    testDataList.append('vOffsetFine,' + str(vOffsetFine))
    if vOffsetCoarse > 9:
        testDataList.insert(1,'vOffsetCoarse failed, must be < 9V, vout = ' + str(vout) + ', vOffsetCoarse = ' + str(vOffsetCoarse))
        return 0
    else:
        if not I2CWrite(0x88):
            return 0
        else:
            #at this point the UUT should adjust its vout
            #option to check the output to validate UUT response
            voutExpected = (vout*0.09823)/0.004883 #unit=bit
            testDataList.append('voutExpected,' + str(voutExpected))
            if not I2CWrite(0x88):
                return 0
            else:
                #measure vout to verify I2CWrite was received                
                try:
                    vout = float(DmmMeasure())
                    startTime = time.time()
                    #wait until vout turns off and then send I2CWrite() again
                    while((vout > .5) and ((time.time()-startTime) < 10)):
                        vout = 0 ######## REMOVE vout = 0!!!! ################float(DmmMeasure())
                    if (vout > .5):
                        testDataList.insert(1,'vout failed to turn off after I2C command, vout = ' + str(vout))
                        return 0
                    else:
                        if not I2CWrite(0x88):
                            return 0
                        #measure vout to verify I2CWrite was received
                        else:
                            vout = float(DmmMeasure())
                            startTime = time.time()
                            #wait until vout turns on and then send I2CWrite() again
                            while((vout < .5) and ((time.time()-startTime) < 10)):
                                vout = float(DmmMeasure())
                except ValueError, err:
                    testErrorList.append(err)
                    return 0
                else:
                    vout = 10  ######## DELETE THIS LINE!!! ################
                    if (vout > (10 - .1)) and (vout < (10 + .1)):
                        if not I2CRead(6):
                            return 0
                        else:
                            testDataList.append('vout = ' + str(vout))
                            return 1
                    else:
                        testDataList.append('vout post Cal,' + str(vout))
                        testDataList.insert(1,'vout outside tolerance(10V +-100mV) post calibration, vout = ' + str(vout))
                        return 0

def CloseProgram():
    CloseComports()
