import time
import serial
import glob #finds all the pathnames matching a specified pattern

global dmmCom
global dmmComIsOpen
global eLoadCom
global eLoadComIsOpen
global pSupplyCom
global pSupplyComIsOpen
global comportList

dmmComIsOpen = False
eLoadComIsOpen = False
pSupplyComIsOpen = False
comportList = glob.glob('/dev/ttyUSB*') # get a list of all connected USB serial converter devices

testResultsList = []
testErrorList = []

class ProgExceptions(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

#***************************************************************************
#Test Equipment setup
#***************************************************************************
def SetupComports():
    if len(comportList) > 0:
        if not AssignDMMComport(comportList):
            print 'unable to communicate with dmm'
            return 0
        print comportList
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
def dmmMeasure(measurementType='volt', dmmRange='def', dmmResolution='def'):
    reply = ''
    error = ''
    dmmCom.write('meas:' + measurementType + ':dc? ' + dmmRange + ", " + dmmResolution + '\n')
    queryTime = time.time()
    reply = dmmCom.readline()    
    queryTime = time.time() - queryTime
    if not dmmTimeoutCheck(queryTime, 'dmmMeasure()'):
        dmmCom.write('system:error?\n')
        error = dmmCom.readline()
        testErrorList.append('dmm error response: ' + error)
        raise ValueError('dmm timeout')
    dmmCom.write('system:error?\n')
    error = dmmCom.readline()
    if 'No error' in error:
        return reply
    else:
        testErrorList.append('dmm error : ' + error)
        raise ValueError('dmm error')

def dmmTimeoutCheck(queryTime, taskName):
    #if read op. > 3 sec, generate prog. error
    if queryTime >= 3:
        testErrorList.append('Time-out during: ' + taskName)
        FailRoutine('')
        return 0
    else:
        return 1

def ProgramPic():
    print("ProgramPic function")
    #
    #
    return



def FailRoutine(FailInfoString):
    print(FailInfoString)
    return
    

def EndTest():
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
    
def TestResultToDatabase():
    print("TestRecordToDatabase")
    #
    #
    return

def TalkToIsoBlock(message):
    print("TalkToIsoBlock function")
    #send message to Iso block
    #receive return message from iso block
    #parse the return message
    #return true or false 
    return 1

def CloseProgram():
    CloseComports()
