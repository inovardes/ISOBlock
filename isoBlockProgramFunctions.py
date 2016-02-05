import time
import serial
import glob #used for finding all the pathnames matching a specified pattern
from smbus import SMBus #library for I2C communication
import sys #for closing the program
import RPi.GPIO as GPIO
import numpy as array #for array manipulation
from Tkinter import * #for GUI creation
import threading
from subprocess import Popen, PIPE, STDOUT
import dcload   # BK 8500 com libraries for python, Dave

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
READ_IOUT = 140
READ_DEVICE_INFO = 176
DELTA_OUTPUT_CHANGE = 179
CALIBRATION_ROUTINE = 189	
#I2C Read Device Info Command Extensions
TRIM_DAC_NUM = 7
READ_SER_NO_1 = 9
READ_SER_NO_2 = 10
READ_SER_NO_3 = 11
#VIN_SCALE_FACTOR = 
#VOUT_SCALE_FACTOR = 
ADC_CORRECTIONS = 14

#Test Program Globals
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
#Test Program Variable Assignments
testDataList = ['Test Data List:']
testErrorList = ['Test Error List:']
dmmComIsOpen = False
eLoadComIsOpen = False
pSupplyComIsOpen = False
comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices
picAutoProgramming = False

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
picAutoProgramEnable=36
#GPIO Initializations
GPIO.setwarnings(False) #Disable the warning related to GPIO.setup command: "RuntimeWarning: This channel is already in use, continuing anyway."
GPIO.setmode(GPIO.BOARD) #Refer to RPi header pin# instead of Broadcom pin#
GPIO.setup(syncNotEnable, GPIO.OUT)
GPIO.setup(isoBlockEnable, GPIO.OUT)
GPIO.setup(vinShuntEnable, GPIO.OUT)
GPIO.setup(vinKelvinEnable, GPIO.OUT)
GPIO.setup(voutShuntEnable, GPIO.OUT)
GPIO.setup(voutKelvinEnable, GPIO.OUT)
GPIO.setup(fanEnable, GPIO.OUT)
GPIO.setup(picEnable, GPIO.OUT)
GPIO.setup(picAutoProgramEnable, GPIO.OUT)
GPIO.setup(rPiReset, GPIO.OUT)
GpioInit()

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
    
    #get the input and output shunt resistance measurements
    global inputShuntRes
    global outputShuntRes
    global testDataList
    global testErrorList
    testDataList = ['Test Data List:']
    testErrorList = ['Test Error List:']
    
    GPIO.output(vinShuntEnable, 1) # 0=disable
    inputShuntRes = float(DmmMeasure(measurementType='resistance').strip())
    GPIO.output(vinShuntEnable, 0) # 0=disable
    testDataList.append('inputShuntRes,' + str(inputShuntRes))
    
    GPIO.output(voutShuntEnable, 1) # 0=disable
    outputShuntRes = float(DmmMeasure(measurementType='resistance').strip())
    GPIO.output(voutShuntEnable, 0) # 0=disable
    testDataList.append('outputShuntRes,' + str(outputShuntRes))
    
    textArea.delete(1.0,END) #clear the test update text area
    UpdateTextArea('Begin Test')

    try:
    #Program PIC
        UpdateTextArea('\nProgram PIC:')
        if not ProgramPic():
            UpdateTextArea('Failed to Program PIC')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('PIC successfully programmed')

    #Initial Power-up check
        if not UUTInitialPowerUp():
            UpdateTextArea('Failed Inital Power-up check')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('Passed Initial Power-up check')
        
    #Calibrate Vout
        UpdateTextArea('\nCalibrate UUT Vout:')
        if not VoutCalibration(vout):
            UpdateTextArea('Failed Vout Calibration')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('Passed Vout Calibration')
        
    #Calibrate Iout
        UpdateTextArea('\nCalibrate Iout')
        if not VoutCurrentLimitCalibration():
            UpdateTextArea('Failed Iout Calibration')
            EndOfTestRoutine(1)#argument=1, UUT failed
            return
        UpdateTextArea('Passed Iout Calibration')
        
        #When everything passes make something on the GUI turn green
        EndOfTestRoutine(0)#argument=0, UUT passed                    
        return
    
    except ValueError, err:
        UpdateTextArea(  'Exception response in main program: ' + str(err))        
        EndOfTestRoutine(1)#argument=1, UUT failed
        return

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
    mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
    mainWindow.mainloop()

#GPIO Initializations
def GpioInit():
    GPIO.output(syncNotEnable, 1) # 1=disable so I2C address=0x1E  or else 0=enable, I2C address=0x1F
    GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    GPIO.output(vinShuntEnable, 0) # 0=disable
    GPIO.output(vinKelvinEnable, 0) # 0=disable
    GPIO.output(voutShuntEnable, 0) # 0=disable
    GPIO.output(voutKelvinEnable, 0) # 0=disable
    GPIO.output(fanEnable, 0) # 0=disable
    GPIO.output(picEnable, 0) # 0=disable
    GPIO.output(picAutoProgramEnable, 0) # 0=disable
    GPIO.output(rPiReset, 1) # 0=enable
    return

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

def EndOfTestRoutine(failStatus):
    GpioInit()
    eLoad.TurnLoadOff()
    Psupply_OnOff()
    for index in range(len(testErrorList)):
        UpdateTextArea(testErrorList[index])        
    for index in range(len(testDataList)):
        UpdateTextArea(testDataList[index])
    if failStatus:
        TestResultToDatabase('fail')
        #make GUI turn red
    else:
        TestResultToDatabase('pass')
        #make GUI turn green
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
        EndOfTestRoutine(1)#argument=1, UUT failed
        bus.close()
        GPIO.cleanup()
        CloseComports()
        mainWindow.destroy()
        sys.exit()
    return

def on_closing():
    EndOfTestRoutine(1)#argument=1, UUT failed
    bus.close()
    GPIO.cleanup()
    CloseComports()
    mainWindow.destroy()
    sys.exit()

#***************************************************************************
#USB to Serial Device setup (Test Measurement Equipment
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
        UpdateTextArea('Successfully setup test equipment')
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
        if not EloadResponse(EloadSetup(), 'EloadSetup'):
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
#I2C & Programming Functions 
#***************************************************************************
def ProgramPic():
    if picAutoProgramming:
        #If the "On-the-go" auto programming feature is setup on the PICkit3
        #a routine will need to be written here
        pass
    else:
        GPIO.output(picEnable, 1) # 0=disable
        GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
        #Put Eload in high impedence state
        if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
            return 0
        #turn supply on: 15V = 150, 100mA = 001, On=0
        if not Psupply_OnOff('150', '001', '0'):#(voltLevel, currentLevel, outputCommand)
            return 0
        #check to see if the power supply is in CC mode.  If so, fail the UUT
        if not PsupplyCCModeCheck():
            return 0
        try:
            p = Popen('exagear', stdin=PIPE, stdout=PIPE) #start emulator for running MPLAB for x86 system
            p.stdin.write('/opt/microchip/mplabx/v3.20/mplab_ipe/ipecmd.sh -?') #begin transfering .hex file via MPLAB command line tool
            outputResult = list(p.communicate()) #wait for command to return with a response
            UpdateTextArea('PIC programming output: \n' + str(outputResult[0]))
            if outputResult[1] is None:
                if p.poll() is None:#Check to see if process is still running
                    p.terminate()                
                if not Psupply_OnOff():#turn power supply off: no function arguments = power off
                    return 0
                GPIO.output(picEnable, 0) # 0=disable
                return 1
            else:
                if p.poll() is None:#Check to see if process is still running
                    p.terminate()
                UpdateTextArea('PIC programming failed.  Error: ' + outputResult[1])
                #turn power supply off: no function arguments = power off
                if not Psupply_OnOff():
                    return 0
                GPIO.output(picEnable, 0) # 0=disable
                return 0
        except Exception, err:
            testErrorList.append('Error while programming PIC: ' + str(err))
            UpdateTextArea('Error while programming PIC: ' + str(err))
            return 0

def I2CWrite(command, messageArray):
    UpdateTextArea("write to Arduino register")
    response = ''
    try:
        response = bus.write_i2c_block_data(ADDR, command, messageArray)
        UpdateTextArea(str(response))
    except Exception, err:
        testErrorList.append('Error in I2CWrite \n ' + str(err))
        return [0,response]
    return [1,response]

def I2CRead(command, bytesToRead):
    UpdateTextArea( 'read Arduino register')
    response = ''
    try:            
        response = bus.read_i2c_block_data(ADDR, command, bytesToRead)
        UpdateTextArea(str(response))    
        UpdateTextArea(str(np.asarray(response)))
        result = [1, response]
    except Exception, err:
        testErrorList.append('Error in I2CRead \n' + str(err))
        result = [0,response]
        return result
    return result

#***************************************************************************
#DMM functions
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
    if not EloadResponse(eLoad.SetRemoteControl(), 'SetRemoteControl'):
        return 0
    if not EloadResponse(eLoad.SetMode(mode), 'SetMode(CC)'):
        return 0
    return 1

#if an Eload command returns with an empty string, the command was successfull
def EloadResponse(response, command):
    if response == '':
        return 1
    else:
        testErrorList.append('eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response[1])
        UpdateTextArea('eLoad command error - "' + str(command) + '" :\nResponse from eLoad: ' + response[1])
        return 0

#***************************************************************************
#Psupply Functions
#***************************************************************************
def Psupply_OnOff(voltLevel='008', currentLevel='000', outputCommand='1'):
    global testErrorList
    #by default the function will drive Volt and Current to 0 and turn the Psupply off=1
    #set the voltage
    pSupplyCom.write('SOUT1\r')
    PsupplyRead(pSupplyCom, 'SOUT1')
    pSupplyCom.write('VOLT008\r')
    voltResponse = PsupplyRead(pSupplyCom, 'VOLT008')[0]
    pSupplyCom.write('SOVP' + voltLevel + '\r')
    overVoltResponse = PsupplyRead(pSupplyCom, 'SOVP' + voltLevel)[0]
    pSupplyCom.write('VOLT' + voltLevel + '\r')
    voltResponse = PsupplyRead(pSupplyCom, 'VOLT' + voltLevel)[0]
    #set the current
    pSupplyCom.write('CURR000\r')
    currResponse = PsupplyRead(pSupplyCom, 'CURR000')[0]
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
    else:
        pass
    if (int(currentLevel) < 10) and outputCommand == '0':
        time.sleep(6)#When the psupply is set to low current it will take about 5 sec to reach its set voltage
    time.sleep(1)
    return 1

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
    response = PsupplyTimeoutCheck(pSupplyCom)
    if (response[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom)
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
    response = PsupplyTimeoutCheck(pSupplyCom)
    if (response[1] != 'OK'):
        temp = PsupplyTimeoutCheck(pSupplyCom)
        if not temp[0]:
            testErrorList.append('pSupply failed to return "OK" after CC mode status.')
            return 0
        modeCheck = (int(response[1]) & 1)
        if modeCheck == 1:
            testDataList.insert(1,'UUT drawing more than ' + str(GetPsupplyUpperCurrent()) + '.  Power supply entered into CC mode when power applied')
            return 0 #pSupply in CC mode,i.e., UUT drawing too much current
        else:
            return 1 #pSupply not in CC mode, i.e, UUT isn't drawing too much current
    else:
        testErrorList.append('pSupply didin\'t return CC mode status: ' + str(response[0]) + str(response[1]))
        return 0
    
#***************************************************************************
#UUT Test Functions
#***************************************************************************

def WaitTillUUTVoutIsLessThan(voltage, waitTime):
        GPIO.output(voutKelvinEnable, 1) # 0=disable
        vout = float(DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWrite() again
        UpdateTextArea('Waiting for UUT vout to turn off...')
        while((vout > float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(DmmMeasure())
        GPIO.output(voutKelvinEnable, 0) # 0=disable
        if (vout > float(voltage)):
            UpdateTextArea('vout failed to reach desired level: ' + str(voltage) + 'vout = ' + str(vout))
            testDataList.insert(1,'vout failed to reach desired level: ' + str(voltage) + 'vout = ' + str(vout))
            return 0
        return 1

#*************************
def WaitTillUUTVoutIsGreaterThan(voltage, waitTime):
        GPIO.output(voutKelvinEnable, 1) # 0=disable
        vout = float(DmmMeasure().strip())
        startTime = time.time()
        #wait until vout turns off and then send I2CWrite() again
        UpdateTextArea('Waiting for UUT vout to turn off...')
        while((vout < float(voltage)) and ((time.time()-startTime) < waitTime)):
            vout = float(DmmMeasure())
        GPIO.output(voutKelvinEnable, 0) # 0=disable
        if (vout < float(voltage)):
            UpdateTextArea('vout failed to reach desired level: ' + str(voltage) + 'vout = ' + str(vout))
            testDataList.insert(1,'vout failed to reach desired level: ' + str(voltage) + 'vout = ' + str(vout))
            return 0
        return 1
    
#*************************
def UUTEnterCalibrationMode():
    UpdateTextArea('Putting UUT in calibration mode...')
    #turn supply on: 28.0V = 120, 5.5A = 055, On = 0
    if not (Psupply_OnOff('280', '055', '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    time.sleep(.020)
    if not (Psupply_OnOff('125', '055', '0')):#(voltLevel, currentLevel, outputCommand)
        return 0

    #request read of 6 bytes from the UUT on the I2C bus, result is a list w/ [0] = pass/fail, [1] = data
    readResult = I2CRead(CALIBRATION_ROUTINE, 6)
    if not readResult[0]:
        return 0
	
    #write the same 6 bytes back to the UUT
    response = readResult[1]
    if not I2CWrite(CALIBRATION_ROUTINE, array.asarray(response))[0]:
        return 0
    #UUT should enter calibration mode
    time.sleep(1)
    if not (Psupply_OnOff('280', '055', '0')):#(voltLevel, currentLevel, outputCommand)
        return 0
    if not WaitTillUUTVoutIsGreaterThan(float(8.5), 5):#UUT vout should go to 10.0 +-1.5V, wait 5 seconds
        return 0
    return 1	#successfully in calibration mode

#*************************
def UUTInitialPowerUp():
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    #turn supply on: 28V = 280, 100mA = 001, On=0
    if not Psupply_OnOff('280', '001', '0'):#(voltLevel, currentLevel, outputCommand)
        return 0
    
    #Verify the UUT input current is < 20mA
    GPIO.output(vinShuntEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(vinShuntEnable, 0) # 0=disable
    uutCurrent = vin/inputShuntRes
    testDataList.append('UUTVinCurrent_ISOBlockDisabled,' + str(uutCurrent))
    if uutCurrent > float(.020):
        testDataList.insert(1,'UUT vin current > 20mA.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        UpdateTextArea('UUT vin current > 20mA.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        return 0
    
    #Verify UUT vout < 5.50V
    GPIO.output(voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(voutKelvinEnable, 0) # 0=disable
    testDataList.append('UUTVout_ISOBlockDisabled,' + str(vout))
    if vout >= float(5.50):
        testDataList.insert(1,'UUT vout >= 5.50V.  Failed initial power up.\nMeasured vout = ' + str(vout))
        UpdateTextArea('UUT vout >= 5.50V.  Failed initial power up.\nMeasured vout = ' + str(vout))
        return 0
    
    #increase the power supply current from 100mA to 1A
    if not Psupply_OnOff('280', '010', '0'):
        return 0
    GPIO.output(isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    #Verify the UUT input current is < 95mA
    GPIO.output(vinShuntEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(vinShuntEnable, 0) # 0=disable
    uutCurrent = vin/inputShuntRes
    testDataList.append('UUTVinCurrent_ISOBlockEnabled,' + str(uutCurrent))
    if uutCurrent >= float(.095):
        testDataList.insert(1,'UUT vin current >= 95mA.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        UpdateTextArea('UUT vin current >= 95mA.  Failed initial power up.\nCalculated current = '
                            + str(uutCurrent) + '\nMeasured vin = ' + str(vin) + '\nMeasured vinShuntRes = ' + str(inputShuntRes))
        return 0
    
    #Verify the UUT vout is = 10.0V +- 1.50V
    GPIO.output(voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(voutKelvinEnable, 0) # 0=disable
    testDataList.append('UUTVout_ISOBlockEnabled,' + str(vout))
    if (vout > (float(11.50)) or (vout < float(8.50))):
        testDataList.insert(1,'UUT vout outside tolerance.  Expected voltage = 10.0V +- 1.50V.  Failed initial power up.\nMeasured vout = ' + str(vout)
                            + '\nMeasured outputShuntRes = ' + str(outputShuntRes))
        UpdateTextArea('UUT vout outside tolerance.  Expected voltage = 10.0V +- 1.50V.  Failed initial power up.\nMeasured vout = ' + str(vout)
                            + '\nMeasured outputShuntRes = ' + str(outputShuntRes))
        return 0
    GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    #wait for vout to turn off
    if not WaitTillUUTVoutIsLessThan(float(5.50), 5):#- UUT vout will float somewhere under 5.50V when off, wait 5 seconds for this to happen
        return 0
    return 1    

#*************************
def VoutCalibration(vout):
    vOffsetCoarse = 0
    vOffsetFine = 0
    #turn power supply off
    if not Psupply_OnOff():# no function arguments = power off
        return 0
    #turn eLoad off
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    #Enable ISO Block output
    GPIO.output(isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    #turn cooling fan on
    GPIO.output(fanEnable, 1) # 0=disable
    if not UUTEnterCalibrationMode():
        return 0
    time.sleep(1)
    if not EloadResponse(eLoad.SetMaxCurrent(float(5.1)), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(float(5)), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    #measure vout
    GPIO.output(voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(voutKelvinEnable, 0) # 0=disable
    if vout < 10.0:
        sign = 0
    else:
        sign = 1
    vOffsetCoarse = float((abs(10.0-vout)*0.09823)/(0.0158)) #unit=bit
    vOffsetFine = (128*sign)+int(((abs(10.0-vout)*0.09823)-(vOffsetCoarse*0.0158))/0.0008)#unit=bit
    testDataList.append('vOffsetCoarse,' + str(vOffsetCoarse))
    testDataList.append('vOffsetFine,' + str(vOffsetFine))
    if vOffsetCoarse > 9:
        testDataList.insert(1,'vOffsetCoarse failed, must be > 9V, vout = ' + str(vout) + ', vOffsetCoarse = ' + str(vOffsetCoarse))
        UpdatTextArea('vOffsetCoarse failed, must be > 9V, vout = ' + str(vout) + ', vOffsetCoarse = ' + str(vOffsetCoarse))
        return 0
    if not I2CWrite(DELTA_OUTPUT_CHANGE, [vOffsetFine, vOffsetCoarse])[0]: #send vOffsetCoarse & vOffsetFine to UUT
        return 0
    #Validate that UUT accepted VoutCalibration
    #UUT should turn off if the calibration was accepted
    if not WaitTillUUTVoutIsLessThan(float(5.50), 5):#UUT vout will float somewhere under 5.50V when off, wait 5 seconds for this to happen
        testDataList.insert(1,'UUT vout failed to turn off after calibration commands were sent to the UUT.')
        UpdateTextArea('UUT vout failed to turn off after calibration commands were sent to the UUT.')        
        return 0
    #Verify Calibration
    UpdateTextArea('\nVerify UUT VOUT Calibration...')
    if not ValidateVoutCalibration():
        return 0
    
    UpdateTextArea('vout calibration successfull')
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    if not Psupply_OnOff():# no function arguments = power off
        return 0
    GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    GPIO.output(fanEnable, 0) # 0=disable
    
    return 1

#*************************
#Command UUT to turn back on and then measure vout to validate calibration
def ValidateVoutCalibration():              
    if not I2CWrite(OPERATION, [128])[0]:
        return 0
    #measure vout to verify I2CWrite was received
    UpdateTextArea('Waiting for UUT vout to turn on...')
    #check to see if UUT vout is on, greater than 8.5V, wait 5 seconds for this to happen
    if not WaitTillUUTVoutIsGreaterThan(float(8.5), 5):
        return 0
    #check vout is within tolerance
    GPIO.output(voutKelvinEnable, 1) # 0=disable
    vout = float(DmmMeasure().strip())
    GPIO.output(voutKelvinEnable, 0) # 0=disable
    testDataList.append('vout_postCal,' + str(vout))
    if (vout < (10 - .05)) or (vout > (10 + .05)):
        testDataList.insert(1,'vout outside tolerance(10V +-50mV) post calibration, vout = ' + str(vout))
        UpdateTextArea('vout outside tolerance(10V +-50mV) post calibration, vout = ' + str(vout))
        return 0
           
    return 1

#*************************
def VoutCurrentLimitCalibration():
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    GPIO.output(isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    if not UUTEnterCalibrationMode():
        return 0
    GPIO.output(fanEnable, 1) # 0=disable
    #wait .5 seconds before requesting initialization of output over-current calibration sequence
    time.sleep(.5)
    calDuration = time.time()
    if not I2CWrite(READ_IOUT, [85])[0]:
        return 0
    #wait 100uS before applying the load
    time.sleep(.001)
    if not EloadResponse(eLoad.SetMaxCurrent(float(12.6)), 'SetMaxCurrent'):
        return 0
    if not EloadResponse(eLoad.SetMaxCurrent(float(12.5)), 'SetCCCurrent'):
        return 0
    if not EloadResponse(eLoad.TurnLoadOn(), 'TurnLoadOn'):
        return 0
    #start the output calibration
    if not I2CWrite(READ_IOUT, [85])[0]:
        return 0
    #monitor vout for completion of calibration, wait up to 30 seconds for vout < .5V
    #Do not let the calibration routine exceed 30 seconds
    if not WaitTillUUTVoutIsLessThan(float(0.5),29):
        testDataList.insert(1,'Iout calibration failed.\nNo response from UUT after 30 sec (vout never turned off after calibration command')
        UpdateTextArea('Iout calibration failed.\nNo response from UUT after 30 sec (vout never turned off after calibration command)')
        return 0

    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    #Request the trim value from UUT by writing and then reading the following commands:
    if not I2CWrite(TRIM_DAC_NUM, [READ_DEVICE_INFO])[0]:
        return 0
    readResult = I2CRead(READ_DEVICE_INFO, 1)
    if not readResult[0]:
        return 0
    if (readResult[1] == 0x1) or (readResult[1] == 0xFF):
        testDataList.insert(1,'Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        UpdateTextArea('Iout calibration failed.\nThe "Trim Value" received from the UUT is: ' + str(readResult[1]))
        return 0

    #restore the output as a final check that communication is still good
    if not I2CWrite(OPERATION, [128])[0]:
        return 0
    
    if not WaitTillUUTVoutIsGreaterThan(float(8.5),5):
        testDataList.insert(1,'Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        UpdateTextArea('Iout calibration failed.\nUUT failed to turn back on after a successfull calibration')
        return 0
    
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    
    GPIO.output(fanEnable, 0) # 0=disable
    GPIO.output(isoBlockEnable, 0) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    
    return 1

#*************************
def VinCalibration():
    if not Psupply_OnOff():#turn power supply off: no function arguments = power off
        return 0
    if not EloadResponse(eLoad.TurnLoadOff(), 'TurnLoadOff'):
        return 0
    GPIO.output(isoBlockEnable, 1) # 0=disable, allow isoB to control pin (isoB pulls up to 5V)
    if not UUTEnterCalibrationMode():
        return 0
    time.sleep(.5)
    GPIO.output(vinKelvinEnable, 1) # 0=disable
    vin = float(DmmMeasure().strip())
    GPIO.output(vinKelvinEnable, 0) # 0=disable
    testDataList.append('vin_preCal,' + str(vin))

    #calc expected input voltage, store data, convert to bytes, and write to UUT
    vInExp = uint16((vin * 0.04443)/0.04443)
    testDataList.append('vinCalc_preCal,' + str(vInExp))
    lowerByte = vInExp & 0xff
    upperByte = vInExp >> 8
    vInBytes = GetLowerUpperBytes(vInExp)
    testDataList.append('vInBytes,' + str(vInBytes))
    if not I2CWrite(READ_VIN, [lowerByte, upperByte]):
    	return 0
    #UUT will then make appropriate updates and then turn output off
                    
    #restore the output as a final check that communication is still good
    if not I2CWrite(OPERATION, [128])[0]:
        return 0

    if not WaitTillUUTVoutIsGreaterThan(float(8.5),5):
        testDataList.insert(1,'Vin calibration failed.\nUUT failed to turn vout back on after a successfull calibration')
        UpdateTextArea('Vin calibration failed.\nUUT failed to turn vout back on after a successfull calibration')
        return 0

    if not I2CWrite(READ_DEVICE_INFO, [lowerByte, upperByte]):
        testDataList.insert(1,'Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        UpdateTextArea('Vin calibration failed in the final step.\nThe VINADCCOR operation failed')
        return 0
    adcValue = I2CRead(ADC_CORRECTIONS, 1)
    if not adcValue[0]:
        return 0
    if (int(adcValue[1]) & 0x7F) > 6: #adcValue[1] comes back from UUT as two's compliment - just need magnitude so clear MSB
        testDataList.insert(1,'Vin calibration failed in the final step.\nThe magintude of ADC offset is > 6\nADC offset returned = ' + str(adcValue[1]))
        UpdateTextArea('Vin calibration failed in the final step.\nThe magintude of ADC offset is > 6\nADC offset returned = ' + str(adcValue[1]))
        return 0
    
    return 1
