
import os
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
from ProgConstants import ProgConst #module that contains all program constants, e.g. voltage tolerance (found in: ProgConstants.py)
from pSupplyFunctions import Psupply #module contains variables & functions for power supply operation (found in: PsupplyFunctions.py)
from dmmFunctions import Dmm #module contains variables & functions for DMM operation (found in: dmmFunctions.py)

#RPi I2C Bus setup
bus = SMBus(1)#RPi has 2 I2C buses, specify which one

#Test Program Globals
global UUT_Serial #holds the board serial number entered by User
global testDataList #test program saves all test data here and then outputs to file when the test finishes
global uutSerialNumberData #this will hold the serial data returned by the UUT in the uutSerialNumberData function

#Test Program Variable Assignments
UUT_Serial = ''
testDataList = []

#Class allows for a responsive GUI window (doesn't freeze up) when the main process is running
class NewThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self): #this function runs when an the .start() method is used on an object
        Main()
        #after Main() completes(UUT test), create the object again to be ready for another test
        threading.Thread.__init__(self)

#Object Declarations
global testInProgressThread #Object controls the GUI click events
testInProgressThread = NewThread()
progConst = ProgConst() #object contains program constants from ProgConst class in ProgConstants.py
pSupply = Psupply() #object for controlling the power supply
dmm = Dmm() #object for controlling the power supply
eLoad = dcload.DCLoad()

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
    if not (dmm.dmmComIsOpen and eLoad.eLoadComIsOpen and pSupply.pSupplyComIsOpen):
        return

    global testDataList
    global UUT_Serial

    testDataList = [] #clear out any old lists
    UUT_Serial = '' #make sure old serial data is cleared out
    
    #check to see that the user entered the board serial number
    if not GetSerialNumber():
        return

    mainWindow.configure(background='grey')
    mainWindow.update_idletasks()
        
    textArea.delete(1.0,END) #clear the test update text area
    UpdateTextArea('Begin Test')
    
    try:
        
    #Program PIC
        UpdateTextArea('\nProgramming PIC...')
        if not ProgramPic():
            UpdateTextArea('Failed to Program PIC')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***PIC programming successfull***')
    
    #Initial Power-up check
        UpdateTextArea('\nInitial Power-Up check...')
        if not UUTInitialPowerUp():
            UpdateTextArea('Failed Initial Power-up check')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Passed Initial Power-up check***')

    #Calibrate Vout
        UpdateTextArea('\nCalibrating UUT Vout...')
        if not VoutCalibration():
            UpdateTextArea('Failed Vout Calibration')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Passed Vout Calibration***')
        
    #Calibrate Vout current
        UpdateTextArea('\nCalibrating Vout current...')
        if not VoutCurrentLimitCalibration():
            UpdateTextArea('Failed Iout Calibration')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Passed Vout current Calibration***')

    #Vin Calibration
        UpdateTextArea('\nCalibrating Vin...')
        if not VinCalibration():
            UpdateTextArea('Failed Vin Calibration')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Passed Vin Calibration***')

    #Unique Serial Number Assignment
        UpdateTextArea('\nAssign UUT unique serial number...')
        if not UniqueSerialNumber():
            UpdateTextArea('Failed to give UUT a unique serial number')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Successfully assigned UUT unique serial number***')

    #Output load regulation test
        UpdateTextArea('\nTesting UUT Vout under load...')
        if not LoadLineRegulation():
            UpdateTextArea('UUT failed regulate under load test')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***Passed Vout under load test***')

    #Synchronization Pin test
        UpdateTextArea('\nTesting the UUT synchronizeation pin (SYNC)...')
        if not SynchronizePinFunction():
            UpdateTextArea('UUT failed SYNC pin test')
            EndOfTestRoutine(True)#True=UUT failed
            return
        UpdateTextArea('***UUT passed SYNC pin test***')
        
        testDataList.append('Pass/Fail Result,UUT passed all tests')
        EndOfTestRoutine(False)#False=UUT passed                
        return

    except Exception, err:
        UpdateTextArea('Exception response in main program: ' + str(err))     
        EndOfTestRoutine(True)#True=UUT failed
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
    GPIO.output(progConst.vinShuntEnable, 0) # 0=disable ---> Not used, trace and contact resistances too large to measure the .01 ohm shunt
    GPIO.output(progConst.vinKelvinEnable, 0) # 0=disable ---> Not used, trace and contact resistances too large to measure the .01 ohm shunt
    GPIO.output(progConst.voutShuntEnable, 0) # 0=disable
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
    GPIO.output(progConst.fanEnable, 0) # 0=disable
    GPIO.output(progConst.picEnable, 0) # 0=disable
    GPIO.output(progConst.picAutoProgramEnable, 0) # 0=disable
    GPIO.output(progConst.rPiReset, 1) # 0=enable
    GPIO.output(progConst.i2c_SDA_Lynch, 1) # 0=enable    
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
        if eLoad.eLoadComIsOpen:
            eLoad.TurnLoadOff()
        if pSupply.pSupplyComIsOpen:
            pSupply.PsupplyOnOff()
        return
    except:
        #ignore any errors due to comports already closed or not active
        return

def EndOfTestRoutine(failStatus):
    LeaveInKnownState()
    inputBox.delete(0,END)
    tempString = 'Fail'
    if not failStatus:
        tempString = 'Pass'
    WriteFiles(tempString)    
    if failStatus:
        TestResultToDatabase('fail')
        mainWindow.configure(background='red')
        mainWindow.update_idletasks()
        UpdateTextArea('\n************\nUUT ' + str(UUT_Serial) + ' Failed test.  See output above for details\n************\n')
    else:
        TestResultToDatabase('pass')
        mainWindow.configure(background='green')
        mainWindow.update_idletasks()
        UpdateTextArea('\n************\nUUT ' + str(UUT_Serial) + ' passed all tests successfully!\n************\n')
    return

def WriteFiles(failStatus):

    dateTime = time.strftime('%m.%d.%Y_%H.%M.%S')
    #add the UUT serial number to the list
    workOrder = UUT_Serial[0:5]
    serialNum = UUT_Serial[5:10]
    pathTemp = str(progConst.testResultsPath).strip("'[]")
    #make sure the path exists
    if not os.path.exists(pathTemp + '/' + str(workOrder)):
        os.makedirs(pathTemp + '/' + str(workOrder))

    #Write test data to file
    tempFile = open(pathTemp + '/' + workOrder + '/' + serialNum + '_' + failStatus + '__' + dateTime, 'w')
    #The first for loop writes the measurement label as row 1 into tab seperated columns
    #The second for loop writes the measurement data as row 2 into tab seperated columns
    for index in range(len(testDataList)):            
        i = str(testDataList[index]).find(',',0)
        if i < 0:
            tempString = str(testDataList[index])
        else:
            tempString = str(testDataList[index])[0:i]
        tempFile.write(tempString.strip() + '\t')
    tempFile.write('\n')
    #Now begin writing the measurement data in the next row
    for index in range(len(testDataList)):
        i = str(testDataList[index]).find(',',0)
        if i < 0:
            tempString = testDataList[index]
        else:
            tempString = str(testDataList[index])
            tempString = tempString[(i+1):len(tempString)]
        tempFile.write(tempString + '\t')
    tempFile.close()

    #Write the same measurement data as above for only passed boards into one single file
    #The first for loop writes the measurement label as row 1 into tab seperated columns
    #The second for loop writes the measurement data as row 2 into tab seperated columns
    if (failStatus == 'Pass'):
        testDataList.insert(0,'UUT_SerialNum,' + str(UUT_Serial))
        fileAlreadyExist = os.path.isfile(pathTemp + '/' + workOrder + '/MeasurementData.txt')
        tempFile = open(pathTemp + '/' + workOrder + '/MeasurementData.txt', 'a')
        #don't write the file header if file already exists
        if not fileAlreadyExist:
            for index in range(len(testDataList)):            
                i = str(testDataList[index]).find(',',0)
                if i < 0:
                    tempString = str(testDataList[index])
                else:
                    tempString = str(testDataList[index])[0:i]
                tempFile.write(tempString.strip() + '\t')
            tempFile.write('\n')
        #Now begin writing the measurement data in the next row
        for index in range(len(testDataList)):
            i = str(testDataList[index]).find(',',0)
            if i < 0:
                tempString = testDataList[index]
            else:
                tempString = str(testDataList[index])
                tempString = tempString[(i+1):len(tempString)]
            tempFile.write(tempString + '\t')
        tempFile.write('\n')
        tempFile.close()
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
    global UUT_Serial
    UUT_Serial = inputBox.get()
    if ((len(UUT_Serial) < 10) or (len(UUT_Serial) > 10)):
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

#if an Eload command returns with an empty string, the command was successfull
def EloadResponse(response, command):
    try:
        if response == '':
            return 1
        else:
            testDataList.append('Pass/Fail Result,eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
            UpdateTextArea('eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
            return 0
    except:
        testDataList.append('Pass/Fail Result,eLoad not responding.  eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
        UpdateTextArea('eLoad not responding.  eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response)
        return 0

def PowerSupplyResponse(messageWithTwoElements):
    try:
        if not messageWithTwoElements[0]:
            UpdateTextArea(messageWithTwoElements[1])
            testDataList.append('Pass/Fail Result,' + str(messageWithTwoElements[1]))
            return 0
        return 1
    except Exception, err:
        UpdateTextArea('An err occurred while checking response from power supply.\n' + messageWithTwoElements[1])
        testDataList.append('Pass/Fail Result,An err occurred while checking response from power supply.\n' + messageWithTwoElements[1])

#***************************************************************************
#***************************************************************************
#USB to Serial Device setup (Test Measurement Equipment)
#***************************************************************************
#***************************************************************************
    
def SetupComports():
    comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices
    for index in range(len(comportList)):
        try:
            if ((not dmm.dmmComIsOpen) and dmm.SetupComport(comportList[index])):
                pass
            elif ((not pSupply.pSupplyComIsOpen) and pSupply.AssignPsupplyComport(comportList[index])):
                pass
            elif ((not eLoad.eLoadComIsOpen) and eLoad.Initialize(device=comportList[index], com_port=-1)):
                pass
            else:
                #continue loop to see if other devices register
                UpdateTextArea('Unable to talk to any test equipment using: ')
                UpdateTextArea(comportList[index])
        except Exception, err:
            UpdateTextArea('Exception occurred while setting up comport: \n' + str(comportList[index]) + str(err))
    if pSupply.pSupplyComIsOpen and eLoad.eLoadComIsOpen and dmm.dmmComIsOpen:        
        textArea.delete(1.0,END) #clear the test update text area
        UpdateTextArea('successfully setup test equipment')
        return 1
    else:
        UpdateTextArea('\nUnable to communicate with test equipment. \nEquipment connection status:\n'
                       'DMM = ' + str(dmm.dmmComIsOpen) + '\nElectronic Load = ' +
                       str(eLoad.eLoadComIsOpen) + '\nPower Supply = ' + str(pSupply.pSupplyComIsOpen))
        UpdateTextArea('\nList of connected devices: ')
        for index in range(len(comportList)):
            UpdateTextArea(str(comportList[index]))
        return 0

def CloseComports():
    try:
        if dmm.dmmComIsOpen:
            if dmm.dmmCom.isOpen():
                dmm.dmmCom.close()
        if eLoad.eLoadComIsOpen:
            if eLoad.SerialPortStatus():
                eLoad.CloseSerialPort()
        if pSupply.pSupplyComIsOpen:
            if pSupply.pSupplyCom.isOpen():
                pSupply.pSupplyCom.close()
        return
    except:
        return

#***************************************************************************
#***************************************************************************
#Programming Function 
#***************************************************************************
#***************************************************************************

#PICK 3 "Programming-To-Go" feature - refer to "PICkit_3_User_Guide_51795A(2).pdf"
#The PICK 3 programmer needs to be configured on a Windows machine using MPLAB X IDE
#The configuration will load the .hex firmware file on the programmer & then the
#"Programming-To_Go" feature must be enabled so the test program can execute programming
#by enabling the RPi I/O attached to the programmers hardware switch
    
def ProgramPic():

    #turn power supply off
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):# no function arguments = power off
        return 0
    
    #connect the PIC programmer by enabling the relays connected to UUT
    GPIO.output(progConst.picEnable, 1) # 0=disable

    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    #Turn Eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #turn supply on: 15V = 150, 100mA = 001, On=0
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.programming_V_Limit, progConst.programming_I_Limit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    time.sleep(.5)
   
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
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):# no function arguments = power off
        return 0
    
    #disconnect the PIC programmer by disabling the relays connected to UUT
    GPIO.output(progConst.picEnable, 0) # 0=disable
    return 1

#***************************************************************************
#***************************************************************************
#I2C Functions 
#***************************************************************************
#***************************************************************************

def I2CWriteMultipleBytes(command, messageArray):
    UpdateTextArea("I2C write to UUT")
    response = ''
    try:
        #had trouble with the python numpy module data type
        #the newArray array and following code converts the
        #array to the correct int data type using the numpy
        #method .item.  The regular index operator way didn't work
        #but would convert each element to a numpy.int32 data type
        newArray = [0 for x in range(len(messageArray))]
        for i in range(len(messageArray)):
            newArray[i] = int(messageArray.item(i))
        time.sleep(2)
        response = RetryI2CWriteMultipleBytes(command, newArray)
        wait = time.time()
        #if the write operation failed, try it one more time
        while ((not response) and ((time.time()-wait) < 3)):#send write command to UUT for 3 seconds or until response is received
            time.sleep(1)
            UpdateTextArea('UUT write unsuccessful.  Trying again ---')
            response = RetryI2CWriteMultipleBytes(command, newArray)
    except Exception, err:
        UpdateTextArea('Error in I2C(write) response from UUT : ' + str(err))
        return 0
    return response

def RetryI2CWriteMultipleBytes(command, messageArray):
    response = ''
    try:
        response = bus.write_i2c_block_data(progConst.I2C_ADDR, command, messageArray)
    except Exception, err:
        return 0
    return 1

def I2CReadMultipleBytes(command, bytesToRead):
    UpdateTextArea("I2C read from UUT")
    response = ''
    response = RetryI2CReadMultipleBytes(command, bytesToRead)
    #check for I/O error - response[1] will be empty if I/O error occurred.  Must not be empty for for loop below
    wait = time.time()
    while ((not response[0]) and ((time.time() - wait) < 2)):
        time.sleep(.5)
        response = RetryI2CReadMultipleBytes(command, bytesToRead)
    return response

def RetryI2CReadMultipleBytes(command, bytesToRead):
    response = ''
    try:
        #enable arduino interrupt to begin counting clock signals in prepartion for pulling SDA high
        #which serves to mask over the stop bit that SMBus uses between a write and read combination
        GPIO.output(progConst.i2c_SDA_Lynch, 0) # 0=enable
        response = bus.read_i2c_block_data(progConst.I2C_ADDR, command, bytesToRead)
        GPIO.output(progConst.i2c_SDA_Lynch, 1) # 0=enable        
        UpdateTextArea('I2C response from UUT : ' + str(np.asarray(response)))
        result = [1, np.asarray(response)]
        return result
    except Exception, err:
        UpdateTextArea('Error in I2C read multiple bytes(read retry) : ' + str(err))
        result = [0, response]
    return result

def ReadWriteCombo(command, messageArray, bytesToRead):
        dataToWrite = [messageArray]
        I2CWriteMultipleBytes(command, np.asarray(dataToWrite))
        time.sleep(.5)
        response = RetryI2CReadMultipleBytes(command, bytesToRead)
        return response        

def I2CReadByte(command):
    response = ''
    try:
        response = bus.read_byte_data(0x1E, command)
        result = [1, np.asarray(response)]
        #try again if for some reason it was unsuccessful
        if not result[0]:
            time.sleep(.5)
            response = bus.read_byte_data(0x1E, command)
            result = [1, np.asarray(response)]
    except Exception, err:
        UpdateTextArea('Error in I2C read byte function : ' + str(err))
        result = [0,response]
        return result
    return result        

#***************************************************************************
#UUT Test Functions
#***************************************************************************

def WaitTillUUTVoutIsLessThan(voltage, waitTime):
        GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
        vout = float(dmm.DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWriteMultipleBytes() again
        UpdateTextArea('Waiting for UUT Vout to turn off...')
        while((vout > float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(dmm.DmmMeasure())
        GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
        if (vout > float(voltage)):
            UpdateTextArea('Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            testDataList.append('Pass/Fail Result,Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            return 0
        return 1

#*************************
def WaitTillUUTVoutIsGreaterThan(voltage, waitTime):
        GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
        vout = float(dmm.DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWriteMultipleBytes() again
        UpdateTextArea('Waiting for UUT Vout to turn on...')
        while((vout < float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(dmm.DmmMeasure())
        GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
        if (vout < float(voltage)):
            UpdateTextArea('Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            testDataList.append('Pass/Fail Result,Vout failed to reach desired level: ' + str(voltage) + '\nVout = ' + str(vout))
            return 0
        return 1

#*************************
def CheckUutFirmware():

    #check that the firmware version set in ProgConstants.py matches the 3rd byte from the read operation in UUTEnterCalibrationMode()
    firmVersion = uutSerialNumberData[2]

    #record firmware version
    testDataList.append('firmwareVersion,' + str(firmVersion))

    UpdateTextArea('UUT firmware version: ' + str(firmVersion) + '\nTest program firmware version: ' + str(progConst.firmwareVersion))

    if not (firmVersion == progConst.firmwareVersion):
        UpdateTextArea('UUT firmware version (' + str(firmVersion) + ') didn\'t match version found in ProgConstants.py (' + str(progConst.firmwareVersion) + ')')
        testDataList.append('Pass/Fail Result,UUT firmware version (' + str(firmVersion) + ') didn\'t match version found in ProgConstants.py (' + str(progConst.firmwareVersion) + ')')
        return 0
    
    return 1

#*************************
def UUTEnterCalibrationMode(currentLimit):
    global uutSerialNumberData
    UpdateTextArea('Putting UUT in calibration mode...')
 
    #turn supply on: 28.0V = 280, 5.5A = 055, On = 0
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.cal_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #if no delay given above, there must be at least 20ms delay before next power supply command
    time.sleep(.020)
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.calMode_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    #print bus.read_byte_data(0x1D, 0x33)
    #request read of 6 bytes from the UUT on the I2C bus, result is a list w/ [0] = pass/fail, [1] = data
    
    readResult = I2CReadMultipleBytes(progConst.CALIBRATION_ROUTINE, 6)    
    uutSerialNumberData = readResult[1]
    if not readResult[0]:
        return 0
    
    #write the same 6 bytes back to the UUT
    response = np.asarray(readResult[1])
    repeatI2CCommands = 0
    #if failed to write back to UUT, run the read/write sequence ? number of times
    while ((not I2CWriteMultipleBytes(progConst.CALIBRATION_ROUTINE, np.asarray(response))) and (repeatI2CCommands < 4)):
        readResult = I2CReadMultipleBytes(progConst.CALIBRATION_ROUTINE, 6)    
        uutSerialNumberData = readResult[1]
        if not readResult[0]:
            return 0
        #write the same 6 bytes back to the UUT
        response = np.asarray(readResult[1])
        repeatI2CCommands += 1

    if not (repeatI2CCommands < 4):
        return 0

##    if not I2CWriteMultipleBytes(progConst.CALIBRATION_ROUTINE, np.asarray(response)):
##        return 0
    
    #UUT should enter calibration mode
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.cal_V_Limit, currentLimit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #Tell the UUT to enable Vout via I2C command
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0

    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 10):#UUT vout should go to 10.0 plus or minus 1.5V, wait 10 seconds
        return 0
    
    return 1	#successfully entered into calibration mode

#*************************
def UUTInitialPowerUp():

    #disable the ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #turn the eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    
    #turn supply on: 28V = 280, 100mA = 001, On=0
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.initPwrUp_Psupply_V_Max, progConst.initPwrUp_Psupply_I_Low, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    
    #Verify the UUT input current is < progConst.Vin_initPwrUp_I_VoutOff_Limit
    time.sleep(1)
    uutCurrent = pSupply.GetPsupplyCurrent()

    #record measurement
    testDataList.append('UUTVinCurrent_ISOBlockDisabled,' + str(uutCurrent[1]))
    
    if not uutCurrent[0]:#if an error occurred in the routine, fail the UUT
        return 0

    #check measurement is within tolerance
    if float(uutCurrent[1]) > progConst.Vin_initPwrUp_I_VoutOff_Limit:
        testDataList.append('Pass/Fail Result,UUT vin current > ' + str(progConst.Vin_initPwrUp_I_VoutOff_Limit) + '.  Failed initial power up.\nMeasured current from power supply = '
                            + str(uutCurrent[1]))
        UpdateTextArea('UUT vin current > ' + str(progConst.Vin_initPwrUp_I_VoutOff_Limit) + '.  Failed initial power up.\nMeasured current from power supply = '
                            + str(uutCurrent[1]))
        return 0
    
    #Verify UUT vout < progConst.initPwrUp_VoutOff_Limit
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('UUTVout_ISOBlockDisabled,' + str(vout))

    #check measurement is within tolerance
    if vout >= progConst.initPwrUp_VoutOff_Limit:
        testDataList.append('Pass/Fail Result,UUT vout >= ' + str(progConst.initPwrUp_VoutOff_Limit) + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        UpdateTextArea('UUT vout >= ' + str(progConst.initPwrUp_VoutOff_Limit) + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        return 0
    
    #increase the power supply current from 100mA to 1A
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.initPwrUp_Psupply_V_Max, progConst.initPwrUp_Psupply_I_High, '0')):
        return 0

    #enable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    time.sleep(2)

    #Tell the UUT to enable Vout via I2C command
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0

    #wait for UUT vout to turn on (vout > progConst.UUT_Vout_On)
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 10):
        return 0
    
    #Verify the UUT input current is < progConst.Vin_initPwrUp_I_VoutOn_Limit
    uutCurrent = pSupply.GetPsupplyCurrent()
    
    #record measurement
    testDataList.append('UUTVinCurrent_ISOBlockEnabled,' + str(uutCurrent[1]))
    
    if not uutCurrent[0]:#if an error occurred in the routine, fail the UUT
        return 0

    #check measurement is within tolerance
    if float(uutCurrent[1]) >= progConst.Vin_initPwrUp_I_VoutOn_Limit:
        testDataList.append('Pass/Fail Result,UUT vin current >= ' + str(progConst.Vin_initPwrUp_I_VoutOn_Limit) + '.  Failed initial power up.\nMeasured current from power supply = '
                            + str(uutCurrent[1]) + '\nMeasured vin = ' + str(vin))
        UpdateTextArea('UUT vin current >= ' + str(progConst.Vin_initPwrUp_I_VoutOn_Limit) + '.  Failed initial power up.\nMeasured current from power supply = '
                       + str(uutCurrent[1]) + '\nMeasured vin = ' + str(vin))
        return 0

    #Verify the UUT vout is = progConst.initPwrUp_VoutOn_Limit +- progConst.initPwrUp_VoutOn_Toler
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('UUTVout_ISOBlockEnabled,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.initPwrUp_VoutOn_Limit)
    if (voutAbsDiff > progConst.initPwrUp_VoutOn_Toler):
        testDataList.append('Pass/Fail Result,UUT vout outside tolerance.  Expected voltage = ' + str(progConst.initPwrUp_VoutOn_Limit) + ' +- ' + str(progConst.initPwrUp_VoutOn_Toler) + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        UpdateTextArea('UUT vout outside tolerance.  Expected voltage = ' + str(progConst.initPwrUp_VoutOn_Limit) + ' +- ' + str(progConst.initPwrUp_VoutOn_Toler) + '.  Failed initial power up.\nMeasured vout = ' + str(vout))
        return 0

    #disable ISO Block vout
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #turn off power supply
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):#turn power supply off: no function arguments = power off
        return 0
    
    #wait for vout to turn off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low, 20):#- UUT vout will float somewhere under 5.50V when off, wait 20 seconds for this to happen
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
    GPIO.output(progConst.fanEnable, 1) # 0=disable
    
    if not UUTEnterCalibrationMode(progConst.voutCal_Psupply_I_Limit):#current function arg as string, e.g., '055' = 5.5A
        return 0

    if not CheckUutFirmware():
        return 0

    #setup eload
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.vout_cal_eload_I_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetCCCurrent(progConst.vout_cal_eload_I_CCMode_Set), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    time.sleep(3)
    
    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_preCal,' + str(vout))

    #values and formulas and resulting calculations below are determined per Raytheon documentation: "ISO Block Test Requirements.docx"
    if vout < 10.0:
        sign = 0
    else:
        sign = 1
    vOffsetCoarse = float(int((abs(10.0-vout)*0.09823)/(0.0158))) #unit=bit
    vOffsetFine = (128*sign)+int(round(((abs(10.0-vout)*0.09823)-(vOffsetCoarse*0.0158))/0.0008))#unit=bit

    #record measurements
    testDataList.append('vOffsetCoarse,' + str(vOffsetCoarse))
    testDataList.append('vOffsetFine,' + str(vOffsetFine))

    
    if vOffsetCoarse > 9:
        testDataList.append('Pass/Fail Result,vOffsetCoarse failed, must be < 9V, \nvout = ' + str(vout) + ', \nvOffsetCoarse = ' + str(vOffsetCoarse))
        UpdateTextArea('vOffsetCoarse failed, must be < 9V, \nvout = ' + str(vout) + ', \nvOffsetCoarse = ' + str(vOffsetCoarse))
        return 0

    #write the computed values to the UUT via I2C write command
    time.sleep(2)
    dataToWrite = [vOffsetFine, vOffsetCoarse]
    if not I2CWriteMultipleBytes(progConst.DELTA_OUTPUT_CHANGE, np.asarray(dataToWrite)): #send vOffsetCoarse & vOffsetFine to UUT
        return 0
    
    #Validate that UUT accepted VoutCalibration
    #UUT should turn off if the calibration was accepted
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off, 15):#UUT vout will float somewhere under 5.50V when off, wait 10 seconds for this to happen       
        return 0
    
    #Verify Calibration
    UpdateTextArea('\nVerify UUT Vout Calibration...')
    if not ValidateVoutCalibration():
        return 0

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #turn power supply off
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):# no function arguments = power off
        return 0

    #disable ISO Block vout
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Wait for ISO Block to fully turn off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low, 20):#UUT vout will float somewhere under 5.50V when off, wait 10 seconds for this to happen       
        return 0

    #turn the fan off
    GPIO.output(progConst.fanEnable, 0) # 0=disable

    return 1

#*************************
#Command UUT to turn back on and then measure vout to validate calibration
def ValidateVoutCalibration():

    time.sleep(1)
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0
    
    #measure vout to verify I2CWriteMultipleBytes was received
    #check to see if UUT vout is on, greater than 8.5V, wait 10 seconds for this to happen
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 10):
        return 0
    
    #check vout is within tolerance
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_postCal,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.voutPostCal_V)
    if (voutAbsDiff > progConst.voutPostCal_Toler):
        testDataList.append('Pass/Fail Result,Vout outside tolerance (' + str(progConst.voutPostCal_V) + ' +- ' + str(progConst.voutPostCal_Toler) + ') post calibration, vout = ' + str(vout))
        UpdateTextArea('Vout outside tolerance(' + str(progConst.voutPostCal_V) + ' +- ' + str(progConst.voutPostCal_Toler) + ') post calibration, vout = ' + str(vout))
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

    #initiate calibration cycle by writing to UUT via I2C
    dataToWrite = [85]
    if not I2CWriteMultipleBytes(progConst.READ_IOUT, np.asarray(dataToWrite)):
        return 0
    
    #wait 100uS before applying the load
    time.sleep(.5)
    #time the calibration cycle to ensure the output doesn't stay on longer than 30 seconds
    calDuration = time.time()
    
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.current_cal_eload_I_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetCCCurrent(progConst.current_cal_eload_I_CCMode_Set), 'SetCCCurrent' ):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    time.sleep(2)
    
    #start the output calibration
    dataToWrite = [85]
    if not I2CWriteMultipleBytes(progConst.READ_IOUT, np.asarray(dataToWrite)):
        return 0
    
    #monitor vout for completion of calibration, wait up to 30 seconds for vout < .5V
    #Do not let the calibration routine exceed 30 seconds, minus any delays after load is turned on
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low,27):
        return 0

    #turn eload off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0

    #Request the trim value from UUT by writing and then reading the following commands:
    time.sleep(2)
    dataToWrite = [progConst.TRIM_DAC_NUM]
    if not I2CWriteMultipleBytes(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        return 0
    time.sleep(1)
    readResult = I2CReadMultipleBytes(progConst.READ_DEVICE_INFO, 1)

    #record I2C value returned
    testDataList.append('UUT_DAC_TrimValue,' + str(readResult[1]).strip("[]"))
    
    if not readResult[0]:
        return 0
    
    #occassionally the I2C response will be garbage (either 255 or 118)
    #read value again if the return value is 118
    time.sleep(1)
    if ((readResult[1] == 118) or (readResult[1] == 255)):
        readResult = I2CReadMultipleBytes(progConst.READ_DEVICE_INFO, 1)

        #record I2C value returned
        testDataList.append('UUT_DAC_TrimValue,' + str(readResult[1]))
    
        if not readResult[0]:
            return 0
    
    if ((readResult[1] == 1) or (readResult[1] == 255) or (readResult[1] == 118)):
        testDataList.append('Pass/Fail Result,Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        UpdateTextArea('Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        return 0

    #restore the output as a final check that communication is still good
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0
    
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 10):
        testDataList.append('Pass/Fail Result,Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        UpdateTextArea('Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        return 0

    #turn power supply off
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):#turn power supply off: no function arguments = power off
        return 0

    #turn fan off
    GPIO.output(progConst.fanEnable, 0) # 0=disable

    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Wait for ISO Block to fully turn off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off, 10):#UUT vout will float somewhere under 5.50V when off, wait 10 seconds for this to happen       
        return 0
    
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
    time.sleep(1)

    #measure Vin using Kelvin measurement
    GPIO.output(progConst.vinKelvinEnable, 1) # 0=disable
    vin = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.vinKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vin_Measured_preCal,' + str(vin))

    #calc expected input voltage, store data, convert to bytes, and write to UUT
    vInExp = np.uint16(round((vin * 0.04443)/0.004883))

    #recored calculation
    testDataList.append('VinExpected,' + str(vInExp))

    #convert to bytes
    vinlowerByte = vInExp & 0xff
    vinupperByte = vInExp >> 8

    #record calculation
    testDataList.append('VinLowerByte,' + str(vinlowerByte))
    testDataList.append('VinUpperByte,' + str(vinupperByte))

    dataToWrite = [vinlowerByte, vinupperByte]
    if not I2CWriteMultipleBytes(progConst.READ_VIN, np.asarray(dataToWrite)):
    	return 0
    
    #UUT will then make appropriate updates and then turn output off
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low,20):
        return 0
                    
    #restore the output as a final check that communication is still good
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0

    
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On,10):
        testDataList.append('Pass/Fail Result,Vin calibration failed.\nUUT failed to turn Vout back on after a successfull calibration')
        UpdateTextArea('Vin calibration failed.\nUUT failed to turn Vout back on after a successfull calibration')
        return 0

    dataToWrite = [progConst.ADC_CORRECTIONS]
    if not I2CWriteMultipleBytes(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
        testDataList.append('Pass/Fail Result,Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        UpdateTextArea('Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        return 0    
    adcValue = I2CReadMultipleBytes(progConst.READ_DEVICE_INFO, 1)
    
    #record value returned from I2C read
    testDataList.append('ADC_CorrectionValue,' + str(adcValue[1]).strip("[]"))
    
    #the first byte received will be a two's complement signed char representing the input ADC offset.
    if not adcValue[0]:
        return 0

    #If the magnitude of the obtained signed char is greater than 6, then the output failed
    if (int(adcValue[1]) & 0x7F) > 6: #adcValue[1] comes back from UUT as two's compliment - just need magnitude so clear MSB
        #try reading the value another time in case the read value was garbage
        dataToWrite = [progConst.ADC_CORRECTIONS]
        if not I2CWriteMultipleBytes(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite)):
            testDataList.append('Pass/Fail Result,Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
            UpdateTextArea('Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
            return 0
        adcValue = I2CReadMultipleBytes(progConst.READ_DEVICE_INFO, 1)
        
        #record value returned from I2C read
        testDataList.append('ADC_CorrectionValue,' + str(adcValue[1]).strip("[]"))
        
        #the first byte received will be a two's complement signed char representing the input ADC offset.
        if not adcValue[0]:
            return 0

        if (int(adcValue[1]) & 0x7F) > 6:
            testDataList.append('Pass/Fail Result,Vin calibration failed in the final step.\nThe magintude of ADC offset is > 6\nADC offset returned = ' + str(adcValue[1]))
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

    #write serial number data to the UUT via I2C.  The serial number will be cut up into pieces and sent in chunks to different registers of the UUT    
    wo = UUT_Serial[0:5]    
    ser = UUT_Serial[5:10]

    #The command extension required to initiate the writing of the serial data
    temp = [progConst.READ_SER_NO_1]

    #seperate out the lower byte of the work order
    tempPlaceHolder = int(wo) & 0xFF
    temp.append(tempPlaceHolder)

    #seperate out the middle byte of the work order
    tempPlaceHolder = int(wo) & 0x3F00
    tempPlaceHolder = tempPlaceHolder >> 8
    temp.append(tempPlaceHolder)

    #the UUT firmware version is the 3rd byte in the transmission and must be inserted here so the ordering remains correct
    #it doesn't matter what value you write as the firmware version since the UUT ignores any write operation to these bits in the register
    temp.append(0x00)

    #seperate out the upper byte of the work order
    tempPlaceHolder = int(wo) & 0xFC000
    tempPlaceHolder = tempPlaceHolder >> 14
    temp.append(tempPlaceHolder)

    #seperate out the lower byte of the serial number
    tempPlaceHolder = int(ser) & 0xFF
    temp.append(tempPlaceHolder)

    #serperate out the upper byte of the serial number
    tempPlaceHolder = int(ser) & 0x3F00
    tempPlaceHolder = tempPlaceHolder >> 8
    temp.append(tempPlaceHolder)

    uutSerialNumberData = temp
    
    UpdateTextArea('Writing unique serial number to UUT...')
    time.sleep(3)
    if not I2CWriteMultipleBytes(progConst.READ_DEVICE_INFO, np.asarray(uutSerialNumberData)):
        testDataList.append('Pass/Fail Result,Failed to write unique serial number to UUT')
        UpdateTextArea('Failed to write unique serial number to UUT')
        return 0

    #record the serial data
    testDataList.append('BOARDID1_LOW,' + str(uutSerialNumberData[1]))
    testDataList.append('BOARDID1_HIGH,' + str(uutSerialNumberData[2]))
    testDataList.append('BOARDID2_LOW,' + str(uutSerialNumberData[3]))
    testDataList.append('BOARDID2_HIGH,' + str(uutSerialNumberData[4]))
    testDataList.append('BOARDID3_LOW,' + str(uutSerialNumberData[5]))
    testDataList.append('BOARDID3_HIGH,' + str(uutSerialNumberData[6]))
    
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low, 20):#- UUT vout will float somewhere under .50V when off, wait 5 seconds for this to happen
        return 0

    #Turn the UUT back on and check output
    time.sleep(3)
    dataToWrite = [128]
    if not I2CWriteMultipleBytes(progConst.OPERATION, np.asarray(dataToWrite)):
        return 0
    
    #measure vout to verify I2CWriteMultipleBytes was received
    #check to see if UUT vout is on, greater than 8.5V, wait 10 seconds for this to happen
    if not WaitTillUUTVoutIsGreaterThan(progConst.UUT_Vout_On, 10):
        return 0

    #Verify the serial numbers have been written to the device by initiating a one-byte
    #write to the READ_DEVICE_INFO command with the extension codes for READ_SER_NO_1, _2 and _3
    UpdateTextArea('Reading back the unique serial number given to UUT...')

    #There are inconsistencies with reading correct information from UUT due to the Arduino attempting to mask
    #over the first stop bit during a read operation.  So, attempt to read multiple times in hopes of reading
    #back the correct serial data that has been previously (above) written to the UUT

    #compare the serial_1, _2 and _3 to the 6 bytes returned when UUT is put into cal mode.
    #The 6 bytes are stored in the uutSerialNumberData variable and contains the following:
    #uutSerialNumberData = [READ_SER_NO_1, SRN01LO, SRN01HI, SRN02LO, SRN02HI, SRN03LO, SRN03HI]

    numTests = 4
    repeatTestCount = 0
    serial_1_passed = False
    serial_2_passed = False
    serial_3_passed = False
    
    while ((not serial_1_passed) and (repeatTestCount < numTests)):
        returnData = readSerialNum1()
        serial_1 = returnData[1]
        if returnData[0]:
           serial_1_passed = True
        repeatTestCount += 1

    repeatTestCount = 0;
    while ((not serial_2_passed) and (repeatTestCount < numTests)):
        returnData = readSerialNum2()
        serial_2 = returnData[1]
        if returnData[0]:
            serial_2_passed = True
        repeatTestCount += 1

    repeatTestCount = 0;
    while ((not serial_3_passed) and (repeatTestCount < numTests)):
        returnData = readSerialNum3()
        serial_3 = returnData[1]
        if returnData[0]:
            serial_3_passed = True
        repeatTestCount += 1

    if (not (serial_1_passed and serial_2_passed and serial_3_passed)):
        UpdateTextArea('Failed to write unique serial number to UUT. Serial numbers did not match the value written to the UUT.\nserial_1[0] = '
                            + str(serial_1[0]) + '\tBOARDID1_LOW = ' + str(uutSerialNumberData[1]) + '\nserial_1[1] = '
                            + str(serial_1[1]) + '\tBOARDID1_HIGH = ' + str(uutSerialNumberData[2]) + '\nserial_2[0] = '
                            + str(serial_2[0]) + '\tBOARDID2_LOW = ' + str(uutSerialNumberData[3]) + '\nserial_2[1] = '
                            + str(serial_2[1]) + '\tBOARDID2_HIGH = ' + str(uutSerialNumberData[4]) + '\nserial_3[0] = '
                            + str(serial_3[0]) + '\tBOARDID3_LOW = ' + str(uutSerialNumberData[5]) + '\nserial_3[1] = '
                            + str(serial_3[1]) + '\tBOARDID3_HIGH = ' + str(uutSerialNumberData[6]))
        testDataList.append('Pass/Fail Result,Failed to write unique serial number to UUT. Serial numbers did not match the value written to the UUT.\nserial_1[0] = '
                            + str(serial_1[0]) + '\tBOARDID1_LOW = ' + str(uutSerialNumberData[1]) + '\nserial_1[1] = '
                            + str(serial_1[1]) + '\tBOARDID1_HIGH = ' + str(uutSerialNumberData[2]) + '\nserial_2[0] = '
                            + str(serial_2[0]) + '\tBOARDID2_LOW = ' + str(uutSerialNumberData[3]) + '\nserial_2[1] = '
                            + str(serial_2[1]) + '\tBOARDID2_HIGH = ' + str(uutSerialNumberData[4]) + '\nserial_3[0] = '
                            + str(serial_3[0]) + '\tBOARDID3_LOW = ' + str(uutSerialNumberData[5]) + '\nserial_3[1] = '
                            + str(serial_3[1]) + '\tBOARDID3_HIGH = ' + str(uutSerialNumberData[6]))
        
        return 0

    #turn power supply off
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):#turn power supply off: no function arguments = power off
        return 0
    
    #disable ISO Block output
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    return 1

#*************************
def readSerialNum1():

    UpdateTextArea('\nserial_1 : ')
    dataToWrite = [progConst.READ_SER_NO_1]
    serial_1 = ReadWriteCombo(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite), 2)
    if not serial_1[0]:
        return [0, serial_1[1]]

    #The return value from the I2CReadMultipleBytes function returns two values in a List type
    #The second element in the List contains two values which will need to be converted to an array
    serial_1 = serial_1[1]

    if not ((int(serial_1[0]) == int(uutSerialNumberData[1]) and int(serial_1[1]) == (uutSerialNumberData[2]))):
        return [0, serial_1]

    return [1, serial_1]

#*************************
def readSerialNum2():

    UpdateTextArea('\nserial_2 : ')
    dataToWrite = [progConst.READ_SER_NO_2]
    serial_2 = ReadWriteCombo(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite), 2)    
    if not serial_2[0]:
        return [0, serial_2[1]]

    #The return value from the I2CReadMultipleBytes function returns two values in a List type
    #The second element in the List contains two values which will need to be converted to an array
    serial_2 = serial_2[1]
    #the first element in this new variable, serial_2[0], contains bits that are set by the UUT even after writing values
    #in the UniqueSerialNumber() function, 0x00 is written to clear out any bits that can be set.  When reading the values
    #back, the value will be 0xF2, which the way the UUT has set the bits after a read/write operation to this register
    #So, the if statement below has 0xF2 hard coded to check that this is indeed the the value returned by the read
    #operation after the 0x00 is written to the register
    
    if not ((serial_2[0] == 0xF2) and int(serial_2[1] == uutSerialNumberData[4])):
        return [0, serial_2]
                
    return [1, serial_2]

#*************************
def readSerialNum3():

    UpdateTextArea('\nserial_3 : ')
    dataToWrite = [progConst.READ_SER_NO_3]
    serial_3 = ReadWriteCombo(progConst.READ_DEVICE_INFO, np.asarray(dataToWrite), 2)
    if not serial_3[0]:
        return [0, serial_3[1]]

    serial_3 = serial_3[1]
    
    if not ((serial_3[0] == int(uutSerialNumberData[5]) and serial_3[1] == int(uutSerialNumberData[6]))):
        return [0, serial_3]

    return [1, serial_3]

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
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.lineRegCheck_Psupply_V_Mid, progConst.lineRegCheck_Psupply_I_Limit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    
    #Enable ISO Block
    GPIO.output(progConst.isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Measure Vout with a ?A Load and psupply @ ?V
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + str(progConst.lineRegCheck_Psupply_V_Mid) + '_noLoad,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    
    if not (voutAbsDiff < progConst.lineRegCheck_Vout_I_Mid_Toler):
        testDataList.append('Pass/Fail Result,Vout failed under no load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Vout_Limit) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Mid_Toler))
        UpdateTextArea('Vout failed under no load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Vout_Limit) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Mid_Toler))
        return 0

    #Measure vout with a ?A load and psupply ?V
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_Mid_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetCCCurrent(progConst.lineRegCheck_eload_I_Mid_CCMode_Set), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    time.sleep(2)

    #measure
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + str(progConst.lineRegCheck_Psupply_V_Mid) + '_' + str(progConst.lineRegCheck_eload_I_Mid_CCMode_Set) + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff < progConst.lineRegCheck_Vout_I_Low_Toler):
        testDataList.append('Pass/Fail Result,Vout failed under ' + str(progConst.lineRegCheck_eload_I_Mid_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Mid) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Low_Toler))
        UpdateTextArea('Vout failed under ' + str(progConst.lineRegCheck_eload_I_Mid_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Mid) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Low_Toler))
        return 0

    #Measure vout with a ?A load and psupply ?V
    if not EloadResponse(eLoad.SetMaxCurrent(progConst.lineRegCheck_eload_I_High_Limit), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetCCCurrent(progConst.lineRegCheck_eload_I_High_CCMode_Set), 'SetCCCurrent'):
        return 0
    time.sleep(2)

    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + str(progConst.lineRegCheck_Psupply_V_Mid) + '_' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff < progConst.lineRegCheck_Vout_I_Mid_Toler):
        testDataList.append('Pass/Fail Result,Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Mid) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Mid_Toler))
        UpdateTextArea('Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Mid) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_Mid_Toler))
        return 0

    #Measure vout with a ?A load and psupply @ ?V
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.lineRegCheck_Psupply_V_Low, progConst.lineRegCheck_Psupply_I_Limit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #measure vout
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable

    #record measurement
    testDataList.append('Vout_' + str(progConst.lineRegCheck_Psupply_V_Low) + '_' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ',' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff < progConst.lineRegCheck_Vout_I_High_Toler):
        testDataList.append('Pass/Fail Result,Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Low) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_High_Toler))
        UpdateTextArea('Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout)+ '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_Low) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_High_Toler))
        return 0

    #Measure vout with a 10A load and psupply @ 36V
    #vout requirement: 9.50 < vout < 10.50
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.lineRegCheck_Psupply_V_High, progConst.lineRegCheck_Psupply_I_Limit, '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #measure
    GPIO.output(progConst.voutKelvinEnable, 1) # 0=disable
    vout = float(dmm.DmmMeasure().strip())
    GPIO.output(progConst.voutKelvinEnable, 0) # 0=disable
    time.sleep(2)

    #record measurement
    testDataList.append('vout_36V_10A,' + str(vout))

    #check measurement is within tolerance
    voutAbsDiff = abs(vout - progConst.lineRegCheck_Vout_Limit)
    if not (voutAbsDiff < progConst.lineRegCheck_Vout_I_High_Toler):
        testDataList.append('Pass/Fail Result,Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_High) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_High_Toler))
        UpdateTextArea('Vout failed under ' + str(progConst.lineRegCheck_eload_I_High_CCMode_Set) + ' load. Vout = ' + str(vout) + '\nExpected = ' + str(progConst.lineRegCheck_Psupply_V_High) + '\nTolerance = ' + str(progConst.lineRegCheck_Vout_I_High_Toler))
        return 0

    #disable equipment
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):#turn power supply off: no function arguments = power off
        return 0
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    #Turn on fan
    GPIO.output(progConst.fanEnable, 0) # 0=disable

    #wait for UUT Vout to go below .5
    if not WaitTillUUTVoutIsLessThan(progConst.UUT_Vout_Off_Low, 20):#- UUT vout will float somewhere under .50V when off, wait 5 seconds for this to happen
        return 0
    
    return 1

#*************************
def SynchronizePinFunction():

    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    #Ensure ISO Block is disabled
    GPIO.output(progConst.isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)

    #Enable sync pin
    GPIO.output(progConst.syncNotEnable, 0) # 1=disable so I2C address=0x1D  or else 0=enable, I2C address=0x1e

    #turn supply on: 28V = 280, 1A = 010, On=0, 0)
    if not PowerSupplyResponse(pSupply.PsupplyOnOff(progConst.synchPinPsupply_V, progConst.synchPinPsupply_I, '0')):
        return 0

    time.sleep(.5)
    addressValue1 = I2CReadByte(progConst.FREQUENCY_SWITCH)  #I2CReadMultipleBytes(progConst.FREQUENCY_SWITCH, np.asarray(dataToWrite))
    if not addressValue1[0]:
        testDataList.append('Pass/Fail Result,Failed to read I2C address')
        UpdateTextArea('Failed to read I2C address')
        return 0
    if not (addressValue1[1] == 0x06):
        testDataList.append('Pass/Fail Result,Failed I2C address verification.\nExpected address = 0x06\nActual value = ' + str(addressValue1[1]))
        UpdateTextArea('Failed I2C address verification.\nExpected value = 0x06\nActual value = ' + str(addressValue1[1]))
        return 0

    if not PowerSupplyResponse(pSupply.PsupplyOnOff()):#turn power supply off: no function arguments = power off
        return 0
    
    #Disable sync pin
    GPIO.output(progConst.syncNotEnable, 1) # 1=disable so I2C address=0x1D  or else 0=enable, I2C address=0x1C
    
    return 1
    
