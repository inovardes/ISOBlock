
#PICK 3 "Programming-To-Go" feature - refer to "PICkit_3_User_Guide_51795A(2).pdf"
#The PICK 3 programmer needs to be configured on a Windows machine using MPLAB X IDE
#The configuration will load the .hex firmware file on the programmer and then the firmware
#can be loaded simply by enabling the switch on the programmer

import time
import serial
import glob #used for finding all the pathnames matching a specified pattern
from smbus import SMBus #library for I2C communication
import sys #for closing the program
import RPi.GPIO as GPIO
import numpy as np #for array manipulation
from Tkinter import * #for GUI creation
import threading
import dcload   # BK 8500 com libraries for python
from ProgConstants import ProgConst #module that contains all program constants, e.g. voltage toleranc

###I2C Bus setup
bus = SMBus(1)#RPi has 2 I2C buses, specify which one

###RPi GPIO setup
GPIO.setwarnings(False) #Disbale the warnings related to GPIO.setup command: "RuntimeWarnings: This channel is already in use, continue anyway."
GPIO.setmode(GPIO.BOARD) #Refer to RPi header pin# instead of Broadcom pin#

#Test Program Globals
UUT_Serial = '' #holds the board serial number entered by User
global datetime
global dmmCom
global dmmComIsOpen
global eLoad #object for use in the dcload class module
global eLoadCom
global eLoadComIsOpen
global pSupplyCom
global pSupplyComIsOpen
global comportList
global testDataList
global testErrorList
global testProgressList
global picAutoProgramming
global inputShuntRes
global outputShuntRes
global uutSerialNumberData #this will hold the serial data returned by the UUT in the uutSerialNumberData function

#Test Program Variable Assignments
testDataList = ['Test Data List:']
testErrorList = ['Test Error List:']
dmmComIsOpen = False
eLoadComIsOpen = False
pSupplyComIsOpen = False
comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices

#Class allows for a responsive GUI window (doesn't freeze up) when the main process is running
class NewThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        Main()
        threading.Thread.__init__(self)

#Object Declarations
#Object controls the GUI click events
global testInProgressThread
testInProgressThread = NewThread()

#object contains program constants
progConst = ProgConst()

#GUI Configuration Setup
mainWindow = Tk()
mainWindow.title('ISO Block Test')
#Find the middle of the screen so the window will be centered when opened
winHeight = mainWindow.winfo_screenheight()/2
winWidth = mainWindow.winfo_screenwidth()/4
windY = str((mainWindow.winfo_screenheight()/2) - (winHeight/2))
windX = str((mainWindow.winfo_screenwidth()/2) - (winWidth/2))
mainWindow.geometry(str(winWidth) + 'x' + str(winHeight) + "+" + windX + "+" + windY)
#scrollbar = Scrollbar(mainWindow)
textArea = Text(mainWindow, wrap=WORD)#, yscrollcommand=scrollbar.set)

inputBoxLabel = Label(mainWindow, text='Enter Serial#')
inputBox = Entry(mainWindow, textvariable=UUT_Serial, width=10)

#************************************************************************************
#************************************************************************************
#Main Function - Called when the GUI start button is clicked
#************************************************************************************
#************************************************************************************

def Main():

    #If user attempts to test when equipment not present, loop back to GUI
    if not (dmmComIsOpen and eLoadComIsOpen and pSupplyComIsOpen):
        return

    global inputShuntRes
    global outputShuntRes
    global testDataList
    global testErrorList
    global datetime

    #check to see that the user entered the board serial number
    if not GetSerialNumber():
        return

    #Get the current system date and time
    datetime = time.strftime('%m/%d/%Y %H:%M:%S')
    
    testDataList = ['Test Data List:']
    testErrorList = ['Test Error List:']
        
    textArea.delete(1.0,END) #clear the test update text area
    UpdateTextArea('Begin Test')

    
    try:
        #get the input and output shunt resistance measurements:
        #neither measurement is necessary since the current at input
        #can be read from the power supply and the output current is
        #controlled by the electronic load.  However, the inputShuntRes
        #is used in the calculation of the input current in the Initial Power-Up
        GPIO.output(progConst.vinShuntEnable, 1) # 0=disable
        inputShuntRes = float(DmmMeasure(measurementType='resistance').strip())
        print inputShuntRes
        GPIO.output(progConst.vinShuntEnable, 0) # 0=disable
        testDataList.append('inputShuntRes,' + str(inputShuntRes))
        
        GPIO.output(progConst.voutShuntEnable, 1) # 0=disable
        outputShuntRes = float(DmmMeasure(measurementType='resistance').strip())
        print outputShuntRes
        GPIO.output(progConst.voutShuntEnable, 0) # 0=disable
        testDataList.append('outputShuntRes,' + str(outputShuntRes))

    #Program PIC
        UpdateTextArea('\nProgramming PIC...')
        if not ProgramPic():
            UpdateTextArea('Failed to Program PIC')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('PIC programming successfull')

    #Initial Power-up check
        UpdateTextArea('\nInitial Power-Up check...')
        if not UUTInitialPowerUp():
            UpdateTextArea('Failed Initial Power-up check')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('Passed Initial Power-up check')
       
##    #Calibrate Vout
##        UpdateTextArea('\nCalibrating UUT Vout...')
##        if not VoutCalibration():
##            UpdateTextArea('Failed Vout Calibration')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('Passed Vout Calibration')
##        
##    #Calibrate vout current
##        UpdateTextArea('\nCalibrating Vout current...')
##        if not VoutCurrentLimitCalibration():
##            UpdateTextArea('Failed Iout Calibration')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('Passed Vout current Calibration')

##    #Vin Calibration
##        UpdateTextArea('\nCalibrating Vin...')
##        if not VinCalibration():
##            UpdateTextArea('Failed Vin Calibration')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('Passed Vin Calibration')

##    #Unique Serial Number Assignment
##        UpdateTextArea('\nAssign UUT unique serial number...')
##        if not UniqueSerialNumber():
##            UpdateTextArea('Failed to give UUT a unique serial number')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('Successfully assigned UUT unique serial number')

##    #Output load regulation test
##        UpdateTextArea('\nTesting the UUT output load regulation...')
##        if not LoadLineRegulation():
##            UpdateTextArea('UUT failed regulate under load test')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('UUT passed regulate under load test')

##    #Synchronization Pin test
##        UpdateTextArea('\nTesting the UUT synchronizeation pin (SYNC)...')
##        if not LoadLineRegulation():
##            UpdateTextArea('UUT failed SYNC pin test')
##            EndOfTestRoutine(1)#argument=1, UUT failed
##            return
##        UpdateTextArea('UUT passed SYN pin test')
        
        #When everything passes make something on the GUI turn green
        EndOfTestRoutine(0)#argument=0, UUT passed                    
        return

    except Exception, err:
        UpdateTextArea('Exception response in main program: ' + str(err))     
        EndOfTestRoutine(1)#argument=1, UUT failed
        return

#***************************************************************************
#***************************************************************************
#Main Program Functions
#***************************************************************************
#***************************************************************************

#GPIO Initializations
def GpioInit():
    GPIO.output(progConst.syncNotEnable, 1) # 1=disable so I2C address=0x1D  or else 0=enable, I2C address=0x1C
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    GPIO.output(progConst.vinShuntEnable, 0) # 0=disable
    GPIO.output(progConst.vinKelvinEnable, 0) # 0=disable
    GPIO.output(progConst.voutShuntEnable, 0) # 0=disable
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
    GPIO.output(progConst.fanEnable, 0) # 0=disable
    GPIO.output(progConst.picEnable, 0) # 0=disable
    GPIO.output(progConst.picAutoProgramEnable, 0) # 0=disable
    GPIO.output(progConst.rPiReset, 1) # 0=enable
    return

def LoadGUI():
    
    GpioInit()

    inputBoxLabel.pack(anchor=N)
    inputBox.pack(anchor=N)
    StartButton = Button(mainWindow, text='Start Test', command=ThreadService)
    StartButton.pack(anchor=N)
    QuitButton = Button(mainWindow, text='Quit', command=QuitTest)
    QuitButton.pack(anchor=S)
    #scrollbar.pack(side=RIGHT, fill=Y, expand=YES)
    #scrollbar.config(command=textArea.yview)
    textArea.pack(side=RIGHT, fill=BOTH, expand=YES)
    mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
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

def LeaveInKnownState():
    try:
        GpioInit()
        if eLoadComIsOpen:
            eLoad.TurnLoadOff()
        if pSupplyComIsOpen:
            Psupply_OnOff()
        return
    except:
        #ignore any errors due to comports already closed or not active
        return

def EndOfTestRoutine(failStatus):
    LeaveInKnownState()
    inputBox.delete(0,END)
    for index in range(len(testErrorList)):
        UpdateTextArea(testErrorList[index])        
    for index in range(len(testDataList)):
        UpdateTextArea(testDataList[index])
    if failStatus:
        TestResultToDatabase('fail')
        mainWindow.configure(background='red')
        mainWindow.update_idletasks()
        UpdateTextArea('\n************\nUUT Failed test.  See above for details & in "asdf.txt"\n************\n')
    else:
        TestResultToDatabase('pass')
        mainWindow.configure(background='green')
        mainWindow.update_idletasks()
        UpdateTextArea('\n************\nUUT passed all tests successfully!\n************\n')
    return

def UpdateTextArea(message):
    textArea.insert(END, message + '\n')
    mainWindow.update_idletasks()
    textArea.see(END)
    return

def TestResultToDatabase(result):
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
    else:
        LeaveInKnownState()
        bus.close()
        GPIO.cleanup()
        CloseComports()
        mainWindow.destroy()
        sys.exit()
    return

def GetSerialNumber():
    UUT_Serial = inputBox.get()
    if len(UUT_Serial) < 10:
        UpdateTextArea('Please enter a 10 character serial#')
        inputBox.delete(0,END)
        return 0
    return 1

def on_closing():
    LeaveInKnownState()
    bus.close()
    GPIO.cleanup()
    CloseComports()
    mainWindow.destroy()
    sys.exit()

#***************************************************************************
#***************************************************************************
#USB to Serial Device setup (Test Measurement Equipment)
#***************************************************************************
#***************************************************************************
    
def SetupComports():
    global dmmCom
    global dmmComIsOpen
    global eLoadCom
    global eLoadComIsOpen
    global pSupplyCom
    global pSupplyComIsOpen
    for index in range(len(comportList)):
        try:
            tempDevice = serial.Serial(comportList[index], baudrate=9600, timeout=3)
            if tempDevice.isOpen():
                if (not dmmComIsOpen) and AssignDMMComport(tempDevice):
                    dmmCom = tempDevice
                    dmmComIsOpen = True
                elif (not pSupplyComIsOpen) and AssignPsupplyComport(tempDevice):
                    pSupplyCom = tempDevice
                    pSupplyComIsOpen = True
                elif (not eLoadComIsOpen) and AssignEloadComport(tempDevice):
                    eLoadComIsOpen = True
                else:
                    #continue loop to see if other devices register
                    tempDevice.close()
                    UpdateTextArea('Unable to talk to any test equipment using: ')
                    UpdateTextArea(comportList[index])
            else:
                UpdateTextArea( 'Unable to open comport: ' + str(comportList[index]) + '\n')
        except Exception, err:
            UpdateTextArea('Exception occurred while setting up comport: \n' + str(comportList[index]) + str(err))
    if pSupplyComIsOpen and eLoadComIsOpen and dmmComIsOpen:        
        textArea.delete(1.0,END) #clear the test update text area
        UpdateTextArea('successfully setup test equipment')
        return 1
    else:
        UpdateTextArea('\nUnable to communicate with test equipment. \nEquipment connection status:\n'
                       'DMM = ' + str(dmmComIsOpen) + '\nElectronic Load = ' +
                       str(eLoadComIsOpen) + '\nPower Supply = ' + str(pSupplyComIsOpen))
        UpdateTextArea('\nList of connected devices: ')
        for index in range(len(comportList)):
            UpdateTextArea(str(comportList[index]))
        dmmComIsOpen = False
        eLoadComIsOpen = False
        pSupplyComIsOpen = False
        return 0

def CloseComports():
    try:
        if dmmComIsOpen:
            if dmmCom.isOpen():
                dmmCom.close()
        if eLoadComIsOpen:
            if eLoad.SerialPortStatus():
                eLoad.CloseSerialPort()
        if pSupplyComIsOpen:
            if pSupplyCom.isOpen():
                pSupplyCom.close()
        return
    except:
        return

#Called from the SetupComports() function
def AssignDMMComport(device):                            
    device.write('*IDN?\n')
    tempString = device.readline()
    if '34401A' in tempString:
        device.write('system:remote\n')
        return 1                                    
    return 0
                
#Called from the SetupComports() function
def AssignEloadComport(device):
    global eLoad
    eLoad = dcload.DCLoad()
    port = device.port
    device.close()
    try:
        eLoad.Initialize(port, 38400)
    except (RuntimeError, TypeError, NameError):
        device.open()
        return 0

    tempString = eLoad.GetProductInformation()
    if '8500' in tempString:
        if not EloadSetup():
            return 0
        if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
            return 0
        return 1
    else:
        device.open()
        return 0

#Called from the SetupComports() function
def AssignPsupplyComport(device):
    device.timeout = 1
    device.write('SOUT1\r')#try turning the supply off
    PsupplyRead(device, 'SOUT1')
    device.write('SOUT1\r')#send command twice - for some reason the psupply doesn't respond on the first attempt
    response = PsupplyRead(device, 'SOUT1')
    if not (response[0]):
        return 0
    return 1

#***************************************************************************
#***************************************************************************
#Programming Function 
#***************************************************************************
#***************************************************************************

def ProgramPic():

    #turn power supply off
    if not Psupply_OnOff():# no function arguments = power off
        return 0
    
    #connect the PIC programmer by enabling the relays connected to UUT
    GPIO.output(progConst.picEnable, 1) # 0=disable

    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    #Turn Eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #turn supply on: 15V = 150, 100mA = 001, On=0
    if not Psupply_OnOff(progConst.programming_V_Limit, progConst.programming_I_Limit, '0'):#(voltLevel, currentLevel, outputCommand)
        return 0
    time.sleep(.5)

    #check to see if the power supply is in CC mode.  If so, fail the UUT
    #This means the UUT is pulling too much current
    if not PsupplyCCModeCheck():
        return 0
    
    #PICK 3 "Programming-To-Go" feature - refer to "PICkit_3_User_Guide_51795A(2).pdf"
    #Enable the GPIO connected to the PIC programmer button to initiate programming
    GPIO.output(progConst.picAutoProgramEnable, 1) # 0=disable
    time.sleep(1)#hold the switch closed for a sec and then release
    GPIO.output(progConst.picAutoProgramEnable, 0) # 0=disable
    #wait until isoBlockEnable pin gets pulled high after data line settles.  isoBlockEnable is a dual use pin which acts as the data line for the programmer 
    UpdateTextArea('Waiting for programming operation...')
    
    #wait for green status LED to be off before continuing
    time.sleep(5)
    
    #check the programmer status.  Per Microchip "PICkit 3 In-Circuit Debugger/Programmer User's Guide",
    #The status light will be green.  check the green LED for 3 volts via jumper to RPi pin 38
    stateOfPin = GPIO.input(progConst.programmerStatus)#Check for the programmer green status LED
    programmingDone = False
    #wait 10 sec before timing out
    startTime = time.time()
    while((not programmingDone) and ((time.time()-startTime) < 10)):
        stateOfPin = GPIO.input(progConst.programmerStatus)#Check for the programmer green status LED
        if stateOfPin:
            programmingDone = True
    if not programmingDone:
        return 0

    #turn power supply off
    if not Psupply_OnOff():# no function arguments = power off
        return 0
    
    #disconnect the PIC programmer by disabling the relays connected to UUT
    GPIO.output(progConst.picEnable, 0) # 0=disable
    return 1

#***************************************************************************
#***************************************************************************
#I2C Functions 
#***************************************************************************
#***************************************************************************

def I2CWrite(command, messageArray):
    UpdateTextArea("I2C write to UUT")
    try:
        #had trouble with the python numpy module data type
        #the newArray array and following code converts the
        #array to the correct int data type using the numpy
        #method .item.  The regular index operator way didn't work
        #but would convert each element to a numpy.int32 data type
        newArray = [0 for x in range(len(messageArray))]
        for i in range(len(messageArray)):
            newArray[i] = int(messageArray.item(i))
        response = RetryI2CWrite(command, newArray)
        wait = time.time()
        while (not response) and ((time.time() - wait) < 1):#send read command to UUT for 5 seconds or until response is received
            time.sleep(.2)
            response = RetryI2CWrite(command, newArray)
    except Exception, err:
        testErrorList.append('Error in I2C(write) \n ' + str(err))
        UpdateTextArea('Error in I2C(write) response from UUT : ' + str(err))
        return 0
    return response

def RetryI2CWrite(command, messageArray):
    try:
        response = bus.write_i2c_block_data(READ_ADDR, command, messageArray)        
        UpdateTextArea('I2C(write retry) response from UUT : ' + str(response))
    except Exception, err:
        testErrorList.append('Error in I2C(write retry) : ' + str(err))
        UpdateTextArea('Error in I2C(write retry) : ' + str(err))
        return 0
    return 1

def I2CRead(command, bytesToRead):
    UpdateTextArea("I2C read from UUT")
    response = ''
    response = RetryI2CRead(command, bytesToRead)
    wait = time.time()
    while ((not response[0] and ((time.time() - wait) < 1))):#send read command to UUT for 5 seconds or until response is received
           time.sleep(.2)
           response = RetryI2CRead(command, bytesToRead)
    return response

def RetryI2CRead(command, bytesToRead):
    response = ''
    try:
        response = bus.read_i2c_block_data(READ_ADDR, command, bytesToRead)
        UpdateTextArea('I2C(read retry) response from UUT : ' + str(np.asarray(response)))
        result = [1, response]
    except Exception, err:
        testErrorList.append('Error in I2C(read retry) : ' + str(err))
        UpdateTextArea('Error in I2C(read retry) : ' + str(err))
        result = [0,response]
        return result
    return result

#***************************************************************************
#***************************************************************************
#DMM functions
#***************************************************************************
#***************************************************************************

#default function params 'def' allows dmm to automatically select the correct range
#to request a resistance measurement, set measurementType to 'res' 
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
#Eload Functions
#***************************************************************************
def EloadSetup(mode = 'cc'):                        
    #initialize connection, set to mode (def = constant current mode)		#Dave
    #modes are 'cc', 'cv', 'cw', or 'cr' they are NOT case-sensitive
    try:
        if not EloadResponse(eLoad.SetRemoteControl(), 'SetRemoteControl'):
            return 0
        if not EloadResponse(eLoad.SetMode(mode), 'SetMode(CC)'):
            return 0
        return 1
    except:
        testErrorList.append('eLoad is unresponsive.  eLoad command error: set CC mode')
        UpdateTextArea('eLoad is unresponsive.  eLoad command error: set CC mode')
        return 0

#if an Eload command returns with an empty string, the command was successfull
def EloadResponse(response, command):
    try:
        if response == '':
            return 1
        else:
            testErrorList.append('eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
            UpdateTextArea('eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
            return 0
    except:
        testErrorList.append('eLoad not responding.  eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
        UpdateTextArea('eLoad not responding.  eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
        return 0

#***************************************************************************
#Psupply Functions
#***************************************************************************
def Psupply_OnOff(voltLevel='008', currentLevel='000', outputCommand='1'):
    try:
        global testErrorList
        #by default the function will drive Volt and Current to 0 and turn the Psupply off=1
        #set the voltage
        pSupplyCom.write('SOVP' + voltLevel + '\r')
        overVoltResponse = PsupplyRead(pSupplyCom, 'SOVP' + voltLevel)[0]
        pSupplyCom.write('VOLT' + voltLevel + '\r')
        voltResponse = PsupplyRead(pSupplyCom, 'VOLT' + voltLevel)[0]
        #set the current
        pSupplyCom.write('SOCP' + currentLevel + '\r')
        overCurrResponse = PsupplyRead(pSupplyCom, 'SOCP' + currentLevel)[0]
        pSupplyCom.write('CURR' + currentLevel + '\r')
        currResponse = PsupplyRead(pSupplyCom, 'CURR' + currentLevel)[0]
        #turn the output on/off
        pSupplyCom.write('SOUT' + outputCommand + '\r')
        outputCommandResponse = PsupplyRead(pSupplyCom, 'SOUT' + outputCommand)[0]
        if not (overVoltResponse and voltResponse and overCurrResponse and currResponse and outputCommandResponse):
            #Attempt to turn power supply off in case of malfunction
            pSupplyCom.write('SOUT1\n')
            PsupplyRead(pSupplyCom, 'SOUT1')
            testErrorList.append('Power supply Error. Response from supply: \n'
                                 '\noverVoltResponse = ' + str(overVoltResponse) + '\nvoltResponse = ' + str(voltResponse) +
                                 '\noverCurrResponse = ' + str(overCurrResponse) + '\ncurrResponse = ' + str(currResponse) +
                                 '\noutputResponse = ' + str(outputCommandResponse))
            UpdateTextArea("Power supply Error. Response from supply: \n" +
                                 '\noverVoltResponse = ' + str(overVoltResponse) + '\nvoltResponse = ' + str(voltResponse) +
                                 '\noverCurrResponse = ' + str(overCurrResponse) + '\ncurrResponse = ' + str(currResponse) +
                                 '\noutputResponse = ' + str(outputCommandResponse))
            return 0
        if outputCommand == '0':#if turning on power supply, allow settling time
            if not VoltageSettle(voltLevel + '0'):
                return 0
        return 1
    except:
        testErrorList.append('pSupply not responding.')
        UpdateTextArea('pSupply not responding.')
        return 0

def PsupplyRead(device, command):
    response = ''
    global testErrorList
    response = PsupplyTimeoutCheck(device, command)
    if not response[0]:
        return response
    if (response[1] != 'OK'):
        testErrorList.append('Power supply command failed.  Response = ' + str(response))
        return response
    return response

def PsupplyTimeoutCheck(device, command):
    response = ''
    queryTime = time.time()
    temp = device.read()
    if ((time.time() - queryTime) >= 1):
        testErrorList.append('Power supply timeout occurred while sending command: ' + str(command))
        return [0,temp]
    while temp != '\r':        
        response = response + temp
        queryTime = time.time()
        temp = device.read()
        if ((time.time() - queryTime) >= 1):
            testErrorList.append('Power supply timeout occurred while sending command: ' + str(command))
            return [0,temp]
    return [1,response]

def GetPsupplyUpperCurrent():
    pSupplyCom.write('GOCP\r')
    response = PsupplyTimeoutCheck(pSupplyCom, 'GOCP')
    if (response[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom, 'GOCP')
        if not temp[0]:
            testErrorList.append('pSupply failed to return "OK" after checking current limit status.')
            return ''
        else:
            return response[1]
    else:
        testErrorList.append('pSupply didin\'t return current limit status: ' + str(response[0]) + str(response[1]))
        return response[1]


def PsupplyCCModeCheck():
    pSupplyCom.write('GETD\r')
    response = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
    if (response[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            testErrorList.append('pSupply failed to return "OK" after CC mode status.')
            return 0
        modeCheck = (int(response[1]) & 1)#The CC mode bit is the last element of the psupply response string
        if modeCheck == 1:
            testDataList.insert(1,'UUT drawing more than ' + str(GetPsupplyUpperCurrent()) + '.  Power supply entered into CC mode when power applied')
            return 0 #pSupply in CC mode,i.e., UUT drawing too much current
        else:
            return 1 #pSupply not in CC mode, i.e, UUT isn't drawing too much current
    else:
        testErrorList.append('pSupply didin\'t return CC mode status: ' + str(response[0]) + str(response[1]))
        return 0

def VoltageSettle(desiredVoltage):
    pSupplyCom.write('GETD\r')
    returnValue = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
    if (returnValue[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            testErrorList.append('pSupply failed to return "OK" after CC mode status.')
            return 0
    returnValue = returnValue[1]
    newValue = ''
    for i in range(4):#The voltage is held in the upper 4 elements of the psupply return string
        newValue = newValue + returnValue[i]
    newValue = int(newValue)
    settleDifference = abs(newValue - int(desiredVoltage))
    wait = time.time()
    #allow 5 seconds for the power supply to settle to desired voltage
    while ((settleDifference > 10) and ((time.time() - wait) < 10)):
        pSupplyCom.write('GETD\r')
        returnValue = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
        if (returnValue[1] != 'OK'):
            temp = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
            if not temp[0]:
                testErrorList.append('pSupply failed to return "OK" after CC mode status.')
                return 0
        newValue = ''
        returnValue = returnValue[1]
        for i in range(4):
            newValue = newValue + returnValue[i]
        newValue = int(newValue)
        settleDifference = abs(newValue - int(desiredVoltage))
    if settleDifference > 10:
        testErrorList.append('Power supply Error. Failed to settle at the desired voltage: '
                             +  str(desiredVoltage) + '\nActual power supply voltage: ' + str(newValue))
        UpdateTextArea('Power supply Error. Failed to settle at the desired voltage: '
                             +  str(desiredVoltage) + '\nActual power supply voltage: ' + str(newValue))
        return 0
    return 1

def GetPsupplyCurrent():
    pSupplyCom.write('GETD\r')
    returnValue = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
    if (returnValue[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            testErrorList.append('pSupply failed to return "OK" after CC mode status.')
            return [0, returnValue[1]]
    current = ''
    returnValue = returnValue[1]
    for i in range(6, 9, +1):
        current = current + returnValue[i]
    print returnValue
    print current
    current = float(float(current)/1000) #move the decimal left to convert the power supply generic output to real current
    return [1, current]

#***************************************************************************
#UUT Test Functions
#***************************************************************************

def WaitTillUUTVoutIsLessThan(voltage, waitTime):
        GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
        vout = float(DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWrite() again
        UpdateTextArea('Waiting for UUT Vout to turn off...')
        while((vout > float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(DmmMeasure())
        GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
        if (vout > float(voltage)):
            UpdateTextArea('Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            testDataList.insert(1,'Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            return 0
        return 1

#*************************
def WaitTillUUTVoutIsGreaterThan(voltage, waitTime):
        GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
        vout = float(DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWrite() again
        UpdateTextArea('Waiting for UUT Vout to turn on...')
        while((vout < float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(DmmMeasure())
        GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
        if (vout < float(voltage)):
            UpdateTextArea('Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            testDataList.insert(1,'Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            return 0
        return 1
    
#*************************
def UUTEnterCalibrationMode(currentLimit):
    global uutSerialNumberData
    UpdateTextArea('Putting UUT in calibration mode...')
    #turn supply on: 28.0V = 280, 5.5A = 055, On = 0
    if not (Psupply_OnOff(progConst.cal_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #Give the UUT time to boot up
    time.sleep(2)
    #if no delay given above, there must be at least 20ms delay before next power supply command
    time.sleep(.020)
    if not (Psupply_OnOff(progConst.calMode_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #request read of 6 bytes from the UUT on the I2C bus, result is a list w/ [0] = pass/fail, [1] = data
    readResult = I2CRead(progConst.CALIBRATION_ROUTINE, 6)
    uutSerialNumberData = readResult[1]

    if not readResult[0]:
        return 0
    
    #write the same 6 bytes back to the UUT
    response = readResult[1]
    #response = [0,0,0,0,0,0]
    if not I2CWrite(progConst.CALIBRATION_ROUTINE, np.asarray(response)):
        return 0
    
    #UUT should enter calibration mode
    time.sleep(1)
    if not (Psupply_OnOff(progConst.cal_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 5):#UUT vout should go to 10.0 plus or minus 1.5V, wait 5 seconds
        return 0
    return 1	#successfuly in calibration mode

#*************************
def UUTInitialPowerUp():

    #disable the ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #turn the eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #turn supply on: 28V = 280, 100mA = 001, On=0
    if not Psupply_OnOff(progConst.initPwrUp_Psupply_V_Max, progConst.initPwrUp_Psupply_I_Low, '0'):#(voltLevel, currentLevel, outputCommand)
        return 0
    time.sleep(.5)
    
    #Verify the UUT input current is < progConst.Vin_initPwrUp_I_VoutOff_Limit
    ###############################
    GPIO.output(progConst.vinShuntEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(progConst.vinShuntEnable, 0) # 0=disable
    print 'voltage across vin shunt'
    print vin
    print 'calculated current'
    print (vin/inputShuntRes)
    ###############################
    uutCurrent = GetPsupplyCurrent()
    print 'psupply current'
    print uutCurrent
    if not uutCurrent[0]:#if an error occurred in the routine, fail the UUT
        return 0

    #record measurement
    testDataList.append('UUTVinCurrent_ISOBlockDisabled,' + str(uutCurrent[1]))

    #check measurement is within tolerance
    if float(uutCurrent[1]) > progConst.Vin_initPwrUp_I_VoutOff_Limit:
        testDataList.insert(1,'UUT vin current > ' + progConst.Vin_initPwrUp_I_VoutOff_Limit + '.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        UpdateTextArea('UUT vin current > ' + progConst.Vin_initPwrUp_I_VoutOff_Limit + '.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        return 0
    
    #Verify UUT vout < progConst.initPwrUp_VoutOff_Limit
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('UUTVout_ISOBlockDisabled,' + str(vout))

    #check measurement is within tolerance
    if vout >= progConst.initPwrUp_VoutOff_Limit:
        testDataList.insert(1,'UUT vout >= ' + progConst.initPwrUp_VoutOff_Limit + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        UpdateTextArea('UUT vout >= ' + progConst.initPwrUp_VoutOff_Limit + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        return 0
    
    #increase the power supply current from 100mA to 1A
    if not Psupply_OnOff(progConst.initPwrUp_Psupply_V_Max, progConst.initPwrUp_Psupply_I_High, '0'):
        return 0
    time.sleep(.5)

    #enable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    time.sleep(.5)

    #wait for UUT vout to turn on (vout > progConst.UUT_Vout_On)
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 5):
        return 0
    
    #Verify the UUT input current is < progConst.Vin_initPwrUp_I_VoutOn_Limit
    uutCurrent = GetPsupplyCurrent()
    if not uutCurrent[0]:#if an error occurred in the routine, fail the UUT
        return 0
    print 'psupply current'
    print uutCurrent
    ###############################
    GPIO.output(progConst.vinShuntEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(progConst.vinShuntEnable, 0) # 0=disable
    print 'voltage across vin shunt'
    print vin
    print 'calculated current'
    print (vin/inputShuntRes)
    ###############################

    #record measurement
    testDataList.append('UUTVinCurrent_ISOBlockEnabled,' + str(uutCurrent[1]))

    #check measurement is within tolerance
    if float(uutCurrent[1]) >= progConst.Vin_initPwrUp_I_VoutOn_Limit:
        testDataList.insert(1,'UUT vin current >= ' + progConst.Vin_initPwrUp_I_VoutOn_Limit + '.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        UpdateTextArea('UUT vin current >= ' + progConst.Vin_initPwrUp_I_VoutOn_Limit + '.  Failed initial power up.\nCalculated current = '
                       + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        return 0

    #Verify the UUT vout is = progConst.initPwrUp_VoutOn_Limit +- progConst.initPwrUp_VoutOn_Toler
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('UUTVout_ISOBlockEnabled,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.initPwrUp_VoutOn_Limit)
    if (voutAbsDiff > progConst.initPwrUp_VoutOn_Toler):
        testDataList.insert(1,'UUT vout outside tolerance.  Expected voltage = ' + progConst.initPwrUp_VoutOn_Limit + ' +- ' + progConst.initPwrUp_VoutOn_Toler + '.  Failed initial power up.\nMeasured vout = ' + str(vout)
                            + '\nMeasured outputShuntRes = ' + str(outputShuntRes))
        UpdateTextArea('UUT vout outside tolerance.  Expected voltage = ' + progConst.initPwrUp_VoutOn_Limit + ' +- ' + progConst.initPwrUp_VoutOn_Toler + '.  Failed initial power up.\nMeasured vout = ' + str(vout)
                            + '\nMeasured outputShuntRes = ' + str(outputShuntRes))
        return 0

    #disable ISO Block vout
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #turn off power supply
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    
    #wait for vout to turn off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off, 5):#- UUT vout will float somewhere under 5.50V when off, wait 5 seconds for this to happen
        return 0
    return 1    

#*************************
def VoutCalibration():
    vOffsetCoarse = 0
    vOffsetFine = 0
    
    #turn eLoad off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #Enable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    #turn cooling fan on
    GPIO.output(fanEnable, 1) # 0=disable
    
    if not UUTEnterCalibrationMode(progConst.voutCal_Psupply_I_Limit):#current function arg as string, e.g., '055' = 5.5A
        return 0
    time.sleep(1)

    #setup eload
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.vout_cal_eload_I_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.vout_cal_eload_I_CCMode_Set), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    
    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #values and formulas and resulting calculations below are determined per Raytheon documentation: "ISO Block Test Requirements.docx"
    if vout < 10.0:
        sign = 0
    else:
        sign = 1
    vOffsetCoarse = float((abs(10.0-vout)*0.09823)/(0.0158)) #unit=bit
    vOffsetFine = (128*sign)+int(round(((abs(10.0-vout)*0.09823)-(vOffsetCoarse*0.0158))/0.0008))#unit=bit

    #record measurements
    testDataList.append('vOffsetCoarse,' + str(vOffsetCoarse))
    testDataList.append('vOffsetFine,' + str(vOffsetFine))

    
    if vOffsetCoarse > 9:
        testDataList.insert(1,'vOffsetCoarse failed, must be < 9V, \nvout = ' + str(vout) + ', \nvOffsetCoarse = ' + str(vOffsetCoarse))
        UpdateTextArea('vOffsetCoarse failed, must be < 9V, \nvout = ' + str(vout) + ', \nvOffsetCoarse = ' + str(vOffsetCoarse))
        return 0

    #write the computed values to the UUT via I2C write commmand
    dataToWrite = [vOffsetFine, vOffsetCoarse]
    if not I2CWrite(DELTA_OUTPUT_CHANGE, np.asarray(dataToWrite)): #send vOffsetCoarse & vOffsetFine to UUT
        return 0
    
    #Validate that UUT accepted VoutCalibration
    #UUT should turn off if the calibration was accepted
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off, 5):#UUT vout will float somewhere under 5.50V when off, wait 5 seconds for this to happen       
        return 0
    
    #Verify Calibration
    UpdateTextArea('\nVerify UUT Vout Calibration...')
    if not ValidateVoutCalibration():
        return 0

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #turn power supply off
    if not Psupply_OnOff():# no function arguments = power off
        return 0

    #disable ISO Block vout
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #turn the fan off
    GPIO.output(progConst.fanEnable, 0) # 0=disable

    return 1

#*************************
#Command UUT to turn back on and then measure vout to validate calibration
def ValidateVoutCalibration():
    dataToWrite = [128]
    if not I2CWrite(OPERATION, np.asarray(dataToWrite)):
        return 0
    
    #measure vout to verify I2CWrite was received
    #check to see if UUT vout is on, greater than 8.5V, wait 5 seconds for this to happen
    if not WaitTillUUTVoutIsGreaterThan(UUT_Vout_On, 5):
        return 0
    
    #check vout is within tolerance
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('vout_postCal,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.voutPostCal_V)
    if (voutAbsDiff > voutPostCal_Toler):
        testDataList.insert(1,'Vout outside tolerance (' + progConst.progConst.voutPostCal_V + ' +- ' + voutPostCal_Toler + ') post calibration, vout = ' + str(vout))
        UpdateTextArea('Vout outside tolerance(' + progConst.progConst.voutPostCal_V + ' +- ' + voutPostCal_Toler + ') post calibration, vout = ' + str(vout))
        return 0
           
    return 1

#*************************
def VoutCurrentLimitCalibration():

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #enable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #put UUT into calibration mode
    if not UUTEnterCalibrationMode(progConst.voutCal_Psupply_I_Limit):#current function arg as string, e.g., '055' = 5.5A
        return 0

    #turn on fan
    GPIO.output(progConst.fanEnable, 1) # 0=disable
    
    #wait .5 seconds before requesting initialization of output over-current calibration sequence
    time.sleep(.5)

    #time the calibration cycle to ensure the output doesn't stay on longer than 30 seconds
    calDuration = time.time()

    #initiate calibration cycle by writing to UUT via I2C
    dataToWrite = [85]
    if not I2CWrite(READ_IOUT, np.asarray(dataToWrite)):
        return 0
    
    #wait 100uS before applying the load
    time.sleep(.001)
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.current_cal_eload_I_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.current_cal_eload_I_CCMode_Set), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    
    #start the output calibration
    dataToWrite = [85]
    if not I2CWrite(progConst.READ_IOUT, np.asarray(dataToWrite)):
        return 0
    
    #monitor vout for completion of calibration, wait up to 30 seconds for vout < .5V
    #Do not let the calibration routine exceed 30 seconds
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low,29):
        return 0

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #Request the trim value from UUT by writing and then reading the following commands:
    dataToWrite = [progConst.TRIM_DAC_NUM]
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        return 0
    readResult = I2CRead(progConst.READ_DEVICE_INFO, 1)
    if not readResult[0]:
        return 0
    
    if (readResult[1] == 0x1) or (readResult[1] == 0xFF):
        testDataList.insert(1,'Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        UpdateTextArea('Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        return 0

    #restore the output as a final check that communication is still good
    dataToWrite = [128]
    if not I2CWrite(OPERATION, np.asarray(dataToWrite)):
        return 0
    
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On,5):
        testDataList.insert(1,'Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        UpdateTextArea('Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        return 0

    #turn power supply off
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0

    #turn fan off
    GPIO.output(progConst.fanEnable, 0) # 0=disable

    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    return 1

#*************************
def VinCalibration():

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #enable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #put UUT in calibration mode
    if not UUTEnterCalibrationMode(progConst.vinCal_Psupply_I_Limit):#current function arg as string, e.g., '015' = 1.5A
        return 0
    time.sleep(.5)

    #measure Vin using Kelvin measurement
    GPIO.output(progConst.vinKelvinEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(progConst.vinKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vin_preCal,' + str(vin))

    #calc expected input voltage, store data, convert to bytes, and write to UUT
    vInExp = np.uint16(round((vin * 0.04443)/0.04443))

    #recored calculation
    testDataList.append('VinCalc_preCal,' + str(vInExp))

    #convert to bytes
    vinlowerByte = vInExp & 0xff
    vinupperByte = vInExp >> 8

    #record calculation
    testDataList.append('VinLowerByte,' + str(vinlowerByte))
    testDataList.append('VinUpperByte,' + str(vinupperByte))

    dataToWrite = [vinlowerByte, vinupperByte]
    if not I2CWrite(READ_VIN, np.asarray(dataToWrite)):
    	return 0
    
    #UUT will then make appropriate updates and then turn output off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low,15):
        return 0
                    
    #restore the output as a final check that communication is still good
    dataToWrite = [128]
    if not I2CWrite(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0

    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On,5):
        testDataList.insert(1,'Vin calibration failed.\nUUT failed to turn Vout back on after a successfull calibration')
        UpdateTextArea('Vin calibration failed.\nUUT failed to turn Vout back on after a successfull calibration')
        return 0

    dataToWrite = [vinlowerByte, vinupperByte]
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        testDataList.insert(1,'Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        UpdateTextArea('Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        return 0    
    adcValue = I2CRead(progConst.ADC_CORRECTIONS, 1)
    
    #the first byte received will be a two's complement signed char representing the input ADC offset.
    if not adcValue[0]:
        return 0

    #If the magnitude of the obtained signed char is greater than 6, then the output failed
    if (int(adcValue[1]) & 0x7F) > 6: #adcValue[1] comes back from UUT as two's compliment - just need magnitude so clear MSB
        testDataList.insert(1,'Vin calibration failed in the final step.\nThe magintude of ADC offset is > 6\nADC offset returned = ' + str(adcValue[1]))
        UpdateTextArea('Vin calibration failed in the final step.\nThe magintude of ADC offset is > 6\nADC offset returned = ' + str(adcValue[1]))
        return 0
    
    return 1

#*************************
def UniqueSerialNumber():
    
    global uutSerialNumberData # the value here is set within the UUTEnterCalibrationMode function

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #Enable ISO Block
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Enter calibration mode
    if not UUTEnterCalibrationMode(progConst.uutSerialNum_Psupply_I_Limit):#current function arg as string, e.g., '015' = 1.5A
        return 0

    #write serial number data to the UUT via I2C
    uutSerialNumberData.insert(1, progConst.READ_SER_NO_1)#prepping uutSerialNumberData to convert to an array and send to UUT
    UpdateTextArea('Writing unique serial number to UUT...')
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(uutSerialNumberData)):
        testDataList.insert(1,'Failed to write unique serial number to UUT')
        UpdateTextArea('Failed to write unique serial number to UUT')
        return 0

    #record the serial data
    testDataList.append('serial_1,' + str(serial_1))
    testDataList.append('uutSerialNumberData[1],' + str(uutSerialNumberData[1]))
    testDataList.append('uutSerialNumberData[2],' + str(uutSerialNumberData[2]))
    testDataList.append('serial_2,' + str(serial_2))
    testDataList.append('uutSerialNumberData[3],' + str(uutSerialNumberData[3]))
    testDataList.append('uutSerialNumberData[4],' + str(uutSerialNumberData[4]))
    testDataList.append('serial_3,' + str(serial_3))
    testDataList.append('uutSerialNumberData[5],' + str(uutSerialNumberData[5]))
    testDataList.append('uutSerialNumberData[6],' + str(uutSerialNumberData[6]))
    
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low, 5):#- UUT vout will float somewhere under .50V when off, wait 5 seconds for this to happen
        return 0

    #Turn the UUT back on and check output
    dataToWrite = [128]
    if not I2CWrite(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0
    
    #measure vout to verify I2CWrite was received
    UpdateTextArea('Waiting for UUT vout to turn on...')
    #check to see if UUT vout is on, greater than 8.5V, wait 5 seconds for this to happen
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 5):
        return 0

    #Verify the serial numbers have been written to the device by initiating a one-byte
    #write to the READ_DEVICE_INFO command with the extension codes for READ_SER_NO_1, _2 and _3
    UpdateTextArea('Reading back the unique serial number given to UUT...')
    dataToWrite = [progConst.READ_SER_NO_1]
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        return 0
    serial_1 = I2CRead(progConst.READ_DEVICE_INFO, 1)

    dataToWrite = [progConst.READ_SER_NO_2]
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        return 0
    serial_2 = I2CRead(progConst.READ_DEVICE_INFO, 1)

    dataToWrite = [progConst.READ_SER_NO_3]
    if not I2CWrite(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        return 0
    serial_3 = I2CRead(progConst.READ_DEVICE_INFO, 1)
    
    if not (serial_1[0] or serial_2[0] or serial_3[0]):
        testDataList.insert(1,'Failed to read back the UUT unique serial number')
        UpdateTextArea('Failed to read back the UUT unique serial number')
        return 0

    #The return value from the I2CRead function returns two values in a List type
    #The second element in the List contains two values which will need to be converted to an array
    serial_1 = np.asarray(serial_1[1])
    serial_2 = np.asarray(serial_2[1])
    serial_3 = np.asarray(serial_3[1])

    #compare the serial_1, _2 and _3 to the 6 bytes returned when UUT is put into cal mode.
    #The 6 bytes are stored in the uutSerialNumberData variable and contains the following:
    #uutSerialNumberData = [READ_SER_NO_1, SRN01LO, SRN01HI, SRN02LO, SRN02HI, SRN03LO, SRN03HI]

    if not (serial_1[0] == uutSerialNumberData[1] and serial_1[1] == uutSerialNumberData[2]):
        testDataList.insert(1,'Failed to write unique serial number to UUT. serial_1 did not match the value written to the UUT.\nserial_1[0] = '
                            + str(serial_1[0]) + '\nuutSerialNumberData[1] == ' + str(uutSerialNumberData[1]) + '\nserial_1[1] = '
                            + str(serial_1[1]) + '\nuutSerialNumberData[2] = ' + str(uutSerialNumberData[2]))
        UpdateTextArea('Failed to write unique serial number to UUT. serial_1 did not match the value written to the UUT.\nserial_1[0] = '
                            + str(serial_1[0]) + '\nuutSerialNumberData[1] == ' + str(uutSerialNumberData[1]) + '\nserial_1[1] = '
                            + str(serial_1[1]) + '\nuutSerialNumberData[2] = ' + str(uutSerialNumberData[2]))
        return 0

    if not (serial_2[0] == uutSerialNumberData[3] and serial_2[1] == uutSerialNumberData[4]):
        testDataList.insert(1,'Failed to write unique serial number to UUT. serial_2 did not match the value written to the UUT.\nserial_2[0] = '
                            + str(serial_2[0]) + '\nuutSerialNumberData[3] == ' + str(uutSerialNumberData[3]) + '\nserial_2[1] = '
                            + str(serial_2[1]) + '\nuutSerialNumberData[4] = ' + str(uutSerialNumberData[4]))
        UpdateTextArea('Failed to write unique serial number to UUT. serial_2 did not match the value written to the UUT.\nserial_2[0] = '
                            + str(serial_2[0]) + '\nuutSerialNumberData[3] == ' + str(uutSerialNumberData[3]) + '\nserial_2[1] = '
                            + str(serial_2[1]) + '\nuutSerialNumberData[4] = ' + str(uutSerialNumberData[4]))
        return 0

    if not (serial_3[0] == uutSerialNumberData[5] and serial_3[1] == uutSerialNumberData[6]):
        testDataList.insert(1,'Failed to write unique serial number to UUT. serial_3 did not match the value written to the UUT.\nserial_3[0] = '
                            + str(serial_3[0]) + '\nuutSerialNumberData[5] == ' + str(uutSerialNumberData[5]) + '\nserial_3[1] = '
                            + str(serial_3[1]) + '\nuutSerialNumberData[6] = ' + str(uutSerialNumberData[6]))
        UpdateTextArea('Failed to write unique serial number to UUT. serial_3 did not match the value written to the UUT.\nserial_3[0] = '
                            + str(serial_3[0]) + '\nuutSerialNumberData[5] == ' + str(uutSerialNumberData[5]) + '\nserial_3[1] = '
                            + str(serial_3[1]) + '\nuutSerialNumberData[6] = ' + str(uutSerialNumberData[6]))
        return 0

    #turn power supply off
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    
    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    return 1

#*************************
def LoadLineRegulation():

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #Ensure ISO Block is disabled
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    #Turn on fan
    GPIO.output(progConst.fanEnable, 1) # 0=disable

    #turn supply on: 28V = 280, 5.5A = 055, On=0
    if not Psupply_OnOff(progConst.lineRegCheck_Psupply_V_Mid, progConst.lineRegCheck_Psupply_I_Limit, '0'):#(voltLevel, currentLevel, outputCommand)
        return 0
    
    #Enable ISO Block
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Measure Vout with a ?A Load and psupply @ ?V
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + progConst.lineRegCheck_Psupply_V_Mid +'_noLoad,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff > progConst.lineRegCheck_Vout_I_Mid_Toler):
        testDataList.insert(1,'Vout failed under no load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Mid_Toler)
        UpdateTextArea('Vout failed under no load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Mid_Toler)
        return 0

    #Measure vout with a ?A load and psupply ?V
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_Mid_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_Mid_CCMode_Set), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0

    #measure
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + progConst.lineRegCheck_Psupply_V_Mid + '_' + progConst.lineRegCheck_eload_I_Mid_CCMode_Set + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff > progConst.lineRegCheck_Vout_I_Low_Toler):
        testDataList.insert(1,'Vout failed under ' + progConst.lineRegCheck_eload_I_Mid_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Low_Toler)
        UpdateTextArea('Vout failed under ' + progConst.lineRegCheck_eload_I_Mid_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Low_Toler)
        return 0

    #Measure vout with a ?A load and psupply ?V
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_High_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_High_CCMode_Set), 'SetCCCurrent'):
        return 0

    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + progConst.lineRegCheck_Psupply_V_Mid + '_' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff > progConst.lineRegCheck_Vout_I_Mid_Toler):
        testDataList.insert(1,'Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Mid_Toler)
        UpdateTextArea('Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Mid + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_Mid_Toler)
        return 0

    #Measure vout with a ?A load and psupply @ ?V
    if not Psupply_OnOff(progConst.lineRegCheck_Psupply_V_Low, progConst.lineRegCheck_Psupply_I_Limit, '0'):#(voltLevel, currentLevel, outputCommand)
        return 0

    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + progConst.lineRegCheck_Psupply_V_Low + '_' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff > progConst.lineRegCheck_Vout_I_High_Toler):
        testDataList.insert(1,'Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Low + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_High_Toler)
        UpdateTextArea('Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_Low + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_High_Toler)
        return 0

    #Measure vout with a 10A load and psupply @ 36V
    #vout requirement: 9.50 < vout < 10.50
    if not Psupply_OnOff(progConst.lineRegCheck_Psupply_V_High, progConst.lineRegCheck_Psupply_I_Limit, '0'):#(voltLevel, currentLevel, outputCommand)
        return 0

    #measure
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('vout_36V_10A,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff > progConst.lineRegCheck_Vout_I_High_Toler):
        testDataList.insert(1,'Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_High + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_High_Toler)
        UpdateTextArea('Vout failed under ' + progConst.lineRegCheck_eload_I_High_CCMode_Set + ' load. Vout = ' + vout + '\nExpected = ' + progConst.lineRegCheck_Psupply_V_High + '\nTolerance = ' + progConst.lineRegCheck_Vout_I_High_Toler)
        return 0

    #disable equipment
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    #Turn on fan
    GPIO.output(progConst.fanEnable, 0) # 0=disable
    
    return 1

#*************************
def SynchronizePinFunction():
    #make sure equipment is turned off
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    #Ensure ISO Block is disabled
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Enable sync pin
    GPIO.output(progConst.syncNotEnable, 0) # 1=disable so I2C address=0x1D  or else 0=enable, I2C address=0x1C

    #turn supply on: 28V = 280, 1A = 010, On=0, 1)
    if not Psupply_OnOff('280', '010', 0):
        return 0

    addressValue1 = I2CRead(0x1F, 1)
    if not addressValue1[0]:
        testDataList.insert(1,'Failed to read I2C address')
        UpdateTextArea('Failed to read I2C addres')
        return 0
    if not (addressValue1[1] == 0x06):
        testDataList.insert(1,'Failed I2C address verification.\nExpected address = 0x06\nActual value = ' + str(addressValue1[1]))
        UpdateTextArea('Failed I2C address verification.\nExpected value = 0x06\nActual value = ' + str(addressValue1[1]))
        return 0
    
    addressValue2 = I2CRead(progConst.FREQUENCY_SWITCH, 1)

    if not addressValue2[0]:
        testDataList.insert(1,'Failed to read I2C address')
        UpdateTextArea('Failed to read I2C address')
        return 0
    if not (addressValue2[1] == 0x06):
        testDataList.insert(1,'Failed I2C address verification.\nExpected address = 0x06\nActual value = ' + str(addressValue2[1]))
        UpdateTextArea('Failed I2C address verification.\nExpected value = 0x06\nActual value = ' + str(addressValue2[1]))
        return 0

    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    
    return 1
    
