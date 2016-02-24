import serial
import glob #used for finding all the pathnames matching a specified pattern
import time


global pSupplyCom
global pSupplyComIsOpen

def SetupComport(tempDevice):
    global pSupplyCom
    global pSupplyComIsOpen
    pSupplyComIsOpen = False
    pSupplyCom = serial.Serial(tempDevice, baudrate=9600, timeout=3)
    if pSupplyCom.isOpen():
        if AssignComport(pSupplyCom):
            pSupplyComIsOpen = True
        else:
            pSupplyCom.close()
    if pSupplyComIsOpen:
        return 1
    else:
        return 0

#Called from the SetupPSupplyComport() function
def AssignComport(device):
    device.timeout = 1
    device.write('SOUT1\r')#try turning the supply off
    PsupplyRead(device, 'SOUT1')
    device.write('SOUT1\r')#send command twice - for some reason the psupply doesn't respond on the first attempt
    response = PsupplyRead(device, 'SOUT1')
    if not (response[0]):
        return 0
    return 1

def Psupply_OnOff(voltLevel='008', currentLevel='000', outputCommand='1'):
    try:
        print 'psupply open boolean'
        print pSupplyComIsOpen
        #by default the function will drive Volt and Current to 0 and turn the Psupply off=1
        #set the voltage
        pSupplyCom.write('SOVP' + voltLevel + '\r')
        overVoltResponse = PsupplyRead(pSupplyCom, 'SOVP' + voltLevel)
        pSupplyCom.write('VOLT' + voltLevel + '\r')
        voltResponse = PsupplyRead(pSupplyCom, 'VOLT' + voltLevel)
        #set the current
        pSupplyCom.write('SOCP' + currentLevel + '\r')
        overCurrResponse = PsupplyRead(pSupplyCom, 'SOCP' + currentLevel)
        pSupplyCom.write('CURR' + currentLevel + '\r')
        currResponse = PsupplyRead(pSupplyCom, 'CURR' + currentLevel)
        #turn the output on/off
        pSupplyCom.write('SOUT' + outputCommand + '\r')
        outputCommandResponse = PsupplyRead(pSupplyCom, 'SOUT' + outputCommand)
        if not (overVoltResponse[0] and voltResponse[0] and overCurrResponse[0] and currResponse[0] and outputCommandResponse[0]):
            #Attempt to turn power supply off in case of malfunction
            pSupplyCom.write('SOUT1\n')
            PsupplyRead(pSupplyCom, 'SOUT1')
            errorReport = 'Power supply Error. Response from supply: \noverVoltResponse = ' + str(overVoltResponse[1]) + '\nvoltResponse = ' + str(voltResponse[1]) + '\noverCurrResponse = ' + str(overCurrResponse[1]) + '\ncurrResponse = ' + str(currResponse[1]) + '\noutputResponse = ' + str(outputCommandResponse[1])
            return [0, errorReport]
        if outputCommand == '0':#if turning on power supply, allow settling time
            if not VoltageSettle(voltLevel + '0'):
                return [0,'']
        return [1,'']
    except Exception, err:
        return [0,'pSupply not responding. Error: ' + str(err)]

def PsupplyRead(device, command):
    response = ''
    response = TimeoutCheck(device, command)
    if not response[0]:
        return response
    if (response[1] != 'OK'):
        response[1] = response[1] + '\nPower supply command failed.  Response = ' + str(response)
        return response
    return response

def TimeoutCheck(device, command):
    response = ''
    queryTime = time.time()
    temp = device.read()
    if ((time.time() - queryTime) >= 1):
        temp = temp + '\nPower supply timeout occurred while sending command: ' + str(command)
        return [0,temp]
    while temp != '\r':        
        response = response + temp
        queryTime = time.time()
        temp = device.read()
        if ((time.time() - queryTime) >= 1):
            temp = temp + '\nPower supply timeout occurred while sending command: ' + str(command)
            return [0,temp]
    return [1,response]

##def GetPsupplyUpperCurrent():
##    pSupplyCom.write('GOCP\r')
##    response = TimeoutCheck(pSupplyCom, 'GOCP')
##    if (response[1] != 'OK'):
##        temp = TimeoutCheck(pSupplyCom, 'GOCP')
##        if not temp[0]:
##            return 'pSupply failed to return "OK" after checking current limit status.'
##        else:
##            return response[1]
##    else:
##        response[1] = response[1] + '\npSupply didin\'t return current limit status: ' + str(response[0]) + str(response[1])
##        return response[1]


def PsupplyCCModeCheck():
    pSupplyCom.write('GETD\r')
    response = TimeoutCheck(pSupplyCom, 'GETD')
    if (response[1] != 'OK'):
        temp = TimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            return [0,'pSupply failed to return "OK" after CC mode status.']
        modeCheck = (int(response[1]) & 1)#The CC mode bit is the last element of the psupply response string
        if modeCheck == 1:
            return [0, 'UUT drawing more than ' + str(GetPsupplyUpperCurrent()) + '.  Power supply entered into CC mode when power applied'] #pSupply in CC mode,i.e., UUT drawing too much current
        else:
            return [1, ''] #pSupply not in CC mode, i.e, UUT isn't drawing too much current
    else:
        return [0, 'pSupply didin\'t return CC mode status: ' + str(response[0]) + str(response[1])]

def VoltageSettle(desiredVoltage):
    pSupplyCom.write('GETD\r')
    returnValue = TimeoutCheck(pSupplyCom, 'GETD')
    if (returnValue[1] != 'OK'):
        temp = TimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            return [0, 'pSupply failed to return "OK" after CC mode status.']
    returnValue = returnValue[1]
    newValue = ''
    for i in range(4):#The voltage is held in the upper 4 elements of the psupply return string
        newValue = newValue + returnValue[i]
    newValue = int(newValue)
    wait = time.time()
    #allow 5 seconds for the power supply to settle to desired voltage
    while (int(newValue) < int(desiredVoltage) and ((time.time() - wait) < 10)):
        pSupplyCom.write('GETD\r')
        returnValue = TimeoutCheck(pSupplyCom, 'GETD')
        if (returnValue[1] != 'OK'):
            temp = TimeoutCheck(pSupplyCom, 'GETD')
            if not temp[0]:
                return [0, 'pSupply failed to return "OK" after CC mode status.']
        newValue = ''
        returnValue = returnValue[1]
        for i in range(4):
            newValue = newValue + returnValue[i]
        newValue = int(newValue)
    if newValue < int(desiredVoltage):
        errorReport = 'Power supply Error. Failed to settle at the desired voltage: ' +  str(desiredVoltage) + '\nActual power supply voltage: ' + str(newValue)
        return [0, errorReport]
    return [1, '']

def GetPsupplyCurrent():
    pSupplyCom.write('GETD\r')
    returnValue = TimeoutCheck(pSupplyCom, 'GETD')
    if (returnValue[1] != 'OK'):
        temp = TimeoutCheck(pSupplyCom, 'GETD')
        if not temp[0]:
            returnValue[1] = returnValue[1] + '\npSupply failed to return "OK" after CC mode status.'
            return [0, returnValue[1]]
    current = ''
    returnValue = returnValue[1]
    for i in range(6, 9, +1):
        current = current + returnValue[i]
    print returnValue
    print current
    current = float(float(current)/1000) #move the decimal left to convert the power supply generic output to real current
    return [1, current]

