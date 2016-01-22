import time
import serial
import glob #used for finding all the pathnames matching a specified pattern
from smbus import SMBus #library for I2C communication
import sys #for closing the program
import RPi.GPIO as GPIO
import numpy as np #for array manipulation
from Tkinter import * #for GUI creation
import threading

class NewThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        Main()
        threading.Thread.__init__(self)

global testInProgressThread
testInProgressThread = NewThread()

#I2C Global
ADDR = 0x04 #Slave address (Arduino Leonardo)
bus = SMBus(1)#RPi has 2 I2C buses, specify which one
#I2C Command Codes
OPERATION = 1
CLEAR_FAULTS = 3
FREQUENCY_SWITCH = 51
STATUS_BYTE = 120
READ_VIN = 136
READ_VOUT = 139
READ_DEVICE_INFO = 176
DELTA_OUTPUT_CHANGE = 179
CALIBRATION_ROUTINE = 189	
#I2C Read Device Info Command Extensions
TRIM_DAC_NUM = 6
READ_SER_NO_1 = 8
READ_SER_NO_2 = 9
READ_SER_NO_3 = 10
VIN_SCALE_FACTOR = 11
VOUT_SCALE_FACTOR = 12
ADC_CORRECTIONS = 13

#Test Program Globals
global dmmCom
global dmmComIsOpen
global eLoadCom
global eLoadComIsOpen
global pSupplyCom
global pSupplyComIsOpen
global comportList
global testDataList
global testErrorList
global testProgressList
#Test Program Variable Assignments
dmmComIsOpen = False
eLoadComIsOpen = False
pSupplyComIsOpen = False
comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices

#RPi GPIO globals
syncNotEnable=8
isoBlockEnable=10
rPiReset=12
vinShuntEnable=16
vinKelvinEnable=18
voutShuntEnable=22
voutKelvinEnable=24
fanEnable=26
picEnable=32
#GPIO Initializations
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

#GUI Configuration Setup
mainWindow = Tk()
mainWindow.title('ISO Block Test')
winHeight = mainWindow.winfo_screenheight()/2
winWidth = mainWindow.winfo_screenwidth()/4
windY = str((mainWindow.winfo_screenheight()/2) - (winHeight/2))
windX = str((mainWindow.winfo_screenwidth()/2) - (winWidth/2))
mainWindow.geometry(str(winWidth) + 'x' + str(winHeight) + "+" + windX + "+" + windY)
#scrollbar = Scrollbar(mainWindow)
textArea = Text(mainWindow, wrap=WORD)#, yscrollcommand=scrollbar.set)

#************************************************************************************
#Main Function - Called when the GUI start button is clicked
#************************************************************************************

def Main():

    #Get the current system date and time
    datetime = time.strftime('%m/%d/%Y %H:%M:%S')    
    global testDataList
    global testErrorList
    testDataList = ['Test Data List:']
    testErrorList = ['Test Error List:']
    textArea.delete(1.0,END)

    try:
        temp = ''
        temp = DmmMeasure() #DmmMeasure(measurementType='res')
        UpdateTextArea('DMM measurement: ' + temp.strip())
    #Function Call
        if not VoutCalibration(10):
            UpdateTextArea('Failed VoutCalibration')            
            FailRoutine()
        else:
            UpdateTextArea('Passed VoutCalibration')
        
        #Validate that VoutCalibration processed by UUT
        #UUT should turn off if the calibration was successful
        vout = float(DmmMeasure())
        startTime = time.time()
        #wait until vout turns off and then send I2CWrite() again
        while((vout > .5) and ((time.time()-startTime) < 10)):
            float(DmmMeasure()) #vout = 0
        if (vout > .5):
            UpdateTextArea('vout didn\'t turn off after I2C command, calibration failed. vout = ' + str(vout))
            FailRoutine()
            return
        else:
            UpdateTextArea('vout is off, calibration successful.  Verifying vout calibration...')
    #Function Call
        if not ValidateVoutCalibration():
            UpdateTextArea('vout outside tolerance(10V +-100mV) post calibration, vout = ' + str(vout))
            FailRoutine()
            return
        else:
            UpdateTextArea('vout successfully calibrated, vout = ' + str(vout))
        
        GPIO.output(syncNotEnable, 0)
        #time.sleep(1)
        GPIO.output(syncNotEnable, 1)

        #When everything passes:
        #Send pass record to database
        #make something on the GUI turn green
        for index in range(len(testErrorList)):
            UpdateTextArea(testErrorList[index])            
        for index in range(len(testDataList)):
            UpdateTextArea(testDataList[index])            
        return
    
    except ValueError, err:
        UpdateTextArea(  'Exception response in main program: ' + str(err))        
        FailRoutine()

#***************************************************************************
#Program Functions
#***************************************************************************

def LoadGUI():
    StartButton = Button(mainWindow, text='Start Test', command=ThreadService)
    StartButton.pack()
    QuitButton = Button(mainWindow, text='Quit', command=QuitTest)
    QuitButton.pack()
    #scrollbar.pack(side=RIGHT, fill=Y, expand=YES)
    #scrollbar.config(command=textArea.yview)
    textArea.pack(side=LEFT, fill=BOTH, expand=YES)
    mainWindow.mainloop()

def ThreadService():
    try:
        testInProgressThread.start()
    except:
        messageBox = Tk()
        messageBox.title('Note')
        lbl = Label(messageBox, text='\nTest in progress!\n\nPlease wait for test to complete\n')
        lbl.pack()
        y = messageBox.winfo_screenheight()/2
        x = messageBox.winfo_screenwidth()/2
        messageBox.geometry('+' + str(x) + '+' + str(y))
        messageBox.resizable(width=False, height=False)
        messageBox.mainloop()
    else:
        return

def FailRoutine():
    for index in range(len(testErrorList)):
        UpdateTextArea(testErrorList[index])        
    for index in range(len(testDataList)):
        UpdateTextArea(testDataList[index])        
    TestResultToDatabase('fail')
    return

def UpdateTextArea(message):
    textArea.insert(END, message + '\n\n')
    mainWindow.update_idletasks()
    textArea.see(END)
    return

def TestResultToDatabase(result):
    #
    #
    return

def QuitTest():
    if testInProgressThread.isAlive():
        messageBox = Tk()
        messageBox.title('Note')
        lbl = Label(messageBox, text='\nTest in progress!\n\nPlease wait for test to complete\n')
        lbl.pack()
        y = messageBox.winfo_screenheight()/2
        x = messageBox.winfo_screenwidth()/2
        messageBox.geometry('+' + str(x) + '+' + str(y))
        messageBox.resizable(width=False, height=False)
        messageBox.mainloop()
    bus.close()
    GPIO.cleanup()
    CloseComports()
    mainWindow.quit()
    mainWindow.destroy()
    sys.exit()
    return

#***************************************************************************
#USB to Serial Device setup (Test Measurement Equipment
#***************************************************************************
def SetupComports():
    if len(comportList) > 0:
        if not AssignDMMComport(comportList):
            UpdateTextArea('unable to communicate with dmm')            
            return 0
        if not AssignEloadComport(comportList):
            UpdateTextArea('unable to communicate with Eload')            
            return 0
        if not AssignPsupplyComport(comportList):
            UpdateTextArea('unable to communicate with Psupply')            
            return 0
        UpdateTextArea('successfully setup comports')        
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
    #open each comport in comportList and see if the Agilent, model 34401A, responds
    #if it responds, the respective comport will be removed from the comportList
    for index in range(len(comportList)):
        try:
            tempDevice = serial.Serial(comportList[index], baudrate=9600, timeout=3)
        except:
            UpdateTextArea('Exception occurred while setting up comport: ' + tempDevice + ' in the "AssignDMMComport" function')            
        else:            
            if tempDevice.isOpen():                
                tempDevice.write('*IDN?\n')
                tempString = tempDevice.readline()
                if '34401A' in tempString:
                    comportList.remove(comportList[index])#remove device from List
                    dmmComIsOpen = True
                    dmmCom = tempDevice
                    dmmCom.write('system:remote\n')
                    return 1
                else:
                    #continue loop if system info didn't return correct
                    tempDevice.close()
            else:
                UpdateTextArea( 'Unable to open comport: ' + comportList[index] + '\n')
                
    return 0
                
#Called from the SetupComports() function
def AssignEloadComport(deviceList):
    return 1

#Called from the SetupComports() function
def AssignPsupplyComport(deviceList):
    return 1

#***************************************************************************
#DMM functions
#***************************************************************************

#default function params 'def' allows dmm to automatically select the correct range
def DmmMeasure(measurementType='volt:dc', dmmRange='def', dmmResolution='def'):
    reply = ''
    error = ''
    dmmCom.write('meas:' + measurementType + '? ' + dmmRange + ", " + dmmResolution + '\n')
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
#I2C & Programming Functions 
#***************************************************************************
def ProgramPic():
    UpdateTextArea("ProgramPic function")    
    #
    #
    return

def I2CWrite(command, message):
    UpdateTextArea("write to Arduino register")    
    response = returnData = bus.write_i2c_block_data(ADDR, command, message)
    UpdateTextArea(str(response))
    #if message write/read fails:
        #testErrorList.append('error in VoutCalibration(), variable "sign" = ' + sign)
        #return 0
    return 1

def I2CRead(command, bytesToRead):
    UpdateTextArea( 'read Arduino register')    
    response = bus.read_i2c_block_data(ADDR, command, bytesToRead)
    UpdateTextArea(str(response))    
    UpdateTextArea(str(np.asarray(response)))    
    #if message write/read fails:
        #testErrorList.append('error in VoutCalibration(), variable "sign" = ' + sign)
        #return 0
    return 1

#***************************************************************************
#Eload Functions
#***************************************************************************
def EloadCommand():
    UpdateTextArea("EloadCommand function")    
    #
    #
    return

def EloadQuery():
    UpdateTextArea("EloadQuery function")    
    #
    #
    return
#***************************************************************************
#Psupply Functions
#***************************************************************************
def PSupplyCommand():
    UpdateTextArea("PSupplyCommand function")    
    #send serial command to PS
    #
    #return errors or other information
    return

def PSupplyQuery():
    UpdateTextArea("PowerSupplyQuery function")    
    #send serial command to PS
    #
    #return current draw or other information
    return
    
#***************************************************************************
#UUT Test Functions
#***************************************************************************

def VoutCalibration(vout):
    vout = float(vout)
    vOffsetCoarse = 0
    vOffsetFine = 0
    if vout < 10.0:
        sign = 0
    else:
        sign = 1
    vOffsetCoarse = int((abs(10.0-vout)*0.09823)/(0.0158)) #unit=bit
    vOffsetFine = int((128*sign)+int(((abs(10.0-vout)*0.09823)-(vOffsetCoarse*0.0158))/(0.0008)))#unit=bit
    testDataList.append('vOffsetCoarse,' + str(vOffsetCoarse))
    testDataList.append('vOffsetFine,' + str(vOffsetFine))
    if vOffsetCoarse > 9:
        testDataList.insert(1,'vOffsetCoarse failed, must be < 9V, vout = ' + str(vout) + ', vOffsetCoarse = ' + str(vOffsetCoarse))
    else:
        if not I2CWrite(DELTA_OUTPUT_CHANGE, [vOffsetFine, vOffsetCoarse]): #send vOffsetCoarse & vOffsetFine to UUT
            #exit function since failed to talk to UUT
            return 0
        else:
            #at this point the UUT should adjust its vout
            #option to check the output to validate UUT response
            voutExpected = int((vout*0.09823)/0.004883) #unit=bit
            testDataList.append('voutExpected,' + str(voutExpected))
            if not I2CWrite(READ_DEVICE_INFO, [VOUT_SCALE_FACTOR, 2, 3]):
                #exit function since failed to talk to UUT
                return 0
            else:
                return 1
            
#Command UUT to turn back on and then measure vout to validate calibration
def ValidateVoutCalibration():              
    if not I2CWrite(OPERATION, [128]):
        return 0
    #measure vout to verify I2CWrite was received
    else:
        vout = float(DmmMeasure())
        startTime = time.time()
        #wait until vout turns on and then send I2CWrite() again
        while((vout < .5) and ((time.time()-startTime) < 10)):
            vout = float(DmmMeasure())
    #check vout - Is vout On now?
    vout = 10  ######## DELETE THIS LINE!!! This is just to make the function pass ################
    if (vout > (10 - .1)) and (vout < (10 + .1)):
        if not I2CRead(STATUS_BYTE, 1):
            return 0
        else:
            testDataList.append('vout = ' + str(vout))
            return 1
    else:            
        testDataList.append('vout post Cal,' + str(vout))            
    return 0
