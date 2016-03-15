import serial
import time

class Psupply:

    pSupplyCom = None
    pSupplyComIsOpen = False

    #Called from the Setupself.pSupplyComport() function
    def AssignPsupplyComport(self, device):
        self.pSupplyCom = serial.Serial(device, baudrate=9600, timeout=1)
        if self.pSupplyCom.isOpen():
            self.pSupplyCom.write('SOUT1\r')#try turning the supply off
            self.PsupplyRead(self.pSupplyCom, 'SOUT1')
            self.pSupplyCom.write('SOUT1\r')#send command twice - for some reason the psupply doesn't respond on the first attempt
            response = self.PsupplyRead(self.pSupplyCom, 'SOUT1')
            if not (response[0]):
                self.pSupplyCom.close()
                return 0
        else:
            #unable to open device as serial port
            return 0
        self.pSupplyComIsOpen = True
        return 1

    def PsupplyOnOff(self, voltLevel='008', currentLevel='000', outputCommand='1'):
        try:
            #by default the function will drive Volt and Current to 0 and turn the Psupply off=1
            #set the voltage
            self.pSupplyCom.write('SOVP' + voltLevel + '\r')
            overVoltResponse = self.PsupplyRead(self.pSupplyCom, 'SOVP' + voltLevel)
            self.pSupplyCom.write('VOLT' + voltLevel + '\r')
            voltResponse = self.PsupplyRead(self.pSupplyCom, 'VOLT' + voltLevel)
            #set the current
            self.pSupplyCom.write('SOCP' + currentLevel + '\r')
            overCurrResponse = self.PsupplyRead(self.pSupplyCom, 'SOCP' + currentLevel)
            self.pSupplyCom.write('CURR' + currentLevel + '\r')
            currResponse = self.PsupplyRead(self.pSupplyCom, 'CURR' + currentLevel)
            #turn the output on/off
            self.pSupplyCom.write('SOUT' + outputCommand + '\r')
            outputCommandResponse = self.PsupplyRead(self.pSupplyCom, 'SOUT' + outputCommand)
            if not (overVoltResponse[0] and voltResponse[0] and overCurrResponse[0] and currResponse[0] and outputCommandResponse[0]):
                #Attempt to turn power supply off in case of malfunction
                self.pSupplyCom.write('SOUT1\n')
                self.PsupplyRead(self.pSupplyCom, 'SOUT1')
                errorReport = 'Power supply Error. Response from supply: \noverVoltResponse = ' + str(overVoltResponse[1]) + '\nvoltResponse = ' + str(voltResponse[1]) + '\noverCurrResponse = ' + str(overCurrResponse[1]) + '\ncurrResponse = ' + str(currResponse[1]) + '\noutputResponse = ' + str(outputCommandResponse[1])
                return [0, errorReport]
            if outputCommand == '0':#if turning on power supply, allow settling time
                voltageSettleResult = self.VoltageSettle(voltLevel + '0')
                if not voltageSettleResult[0]:
                    return [0,voltageSettleResult[1]]
            return [1,'']
        except Exception, err:
            return [0,'pSupply not responding. Error: ' + str(err)]

    def PsupplyRead(self, device, command):
        response = ''
        response = self.TimeoutCheck(device, command)
        if not response[0]:
            return response
        if (response[1] != 'OK'):
            response[1] = response[1] + '\nPower supply command failed.  Response = ' + str(response)
            return response
        return response

    def TimeoutCheck(self, device, command):
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

    def GetPsupplyUpperCurrent(self):
        self.pSupplyCom.write('GOCP\r')
        response = self.TimeoutCheck(self.pSupplyCom, 'GOCP')
        if (response[1] != 'OK'):
            temp = self.TimeoutCheck(self.pSupplyCom, 'GOCP')
            if not temp[0]:
                #testErrorList.append('pSupply failed to return "OK" after checking current limit status.')
                return ''
            else:
                return float(float(response[1])/10)
        else:
            #testErrorList.append('pSupply didn\'t return current limit status: ' + str(response[0]) + str(response[1]))
            return response[1]

#The PsupplyCCModeCheck function is now implemented in the VoltageSettle function because this prevents power being applied
#to the UUT for extended periods of time in the case when the UUT is drawing more than the current upper limit

##    def PsupplyCCModeCheck(self):
##        self.pSupplyCom.write('GETD\r')
##        response = self.TimeoutCheck(self.pSupplyCom, 'GETD')
##        if (response[1] != 'OK'):
##            temp = self.TimeoutCheck(self.pSupplyCom, 'GETD')
##            if not temp[0]:
##                return [0,'pSupply failed to return "OK" after CC mode status.']
##            modeCheck = (int(response[1]) & 1)#The CC mode bit is the last element of the psupply response string
##            if (modeCheck == 1):
##                return [0, 'UUT drawing more than ' + str(self.GetPsupplyUpperCurrent()) + '.  Power supply entered into CC mode when power applied'] #pSupply in CC mode,i.e., UUT drawing too much current
##            else:
##                return [1, ''] #pSupply not in CC mode, i.e, UUT isn't drawing too much current
##        else:
##            return [0, 'pSupply didin\'t return CC mode status: ' + str(response[0]) + str(response[1])]

    def VoltageSettle(self, desiredVoltage):
        self.pSupplyCom.write('GETD\r')
        returnValue = self.TimeoutCheck(self.pSupplyCom, 'GETD')
        if (returnValue[1] != 'OK'):
            temp = self.TimeoutCheck(self.pSupplyCom, 'GETD')
            if not temp[0]:
                return [0, 'pSupply failed to return "OK" after CC mode status.']

        #seperate out the voltage value in the returnValue
        returnValue = returnValue[1]
        newValue = ''
        for i in range(4):#The voltage is held in the upper 4 elements of the psupply return string
            newValue = newValue + returnValue[i]
        newValue = int(newValue)
        settleDifference = abs(newValue - int(desiredVoltage))
        wait = time.time()

        #allow 10 seconds for the power supply to settle to desired voltage
        #the return string from power supply representing the voltage has 4
        #characters, e.g., 2800 = 28.00V, 0302 = 3.02V.  Thus, the while loop
        #below will check that the power supply settles within 10mV of desiredVoltage
        while ((settleDifference > 10) and ((time.time() - wait) < 10)):
            self.pSupplyCom.write('GETD\r')
            returnValue = self.TimeoutCheck(self.pSupplyCom, 'GETD')
            if (returnValue[1] != 'OK'):
                temp = self.TimeoutCheck(self.pSupplyCom, 'GETD')
                if not temp[0]:
                    return [0, 'pSupply failed to return "OK" after CC mode status.']
                
            #Seperate out the voltage value in the returnValue
            newValue = ''
            returnValue = returnValue[1]
            for i in range(4):
                newValue = newValue + returnValue[i]
            newValue = int(newValue)
            settleDifference = abs(newValue - int(desiredVoltage))
        #A 10 second timeout may have occurred while waiting for the voltage to settle.
        #Check that the voltage settled
        if settleDifference > 10:
            errorReport = ('Power supply Error. Failed to settle at the desired voltage : '
                           + str((float(desiredVoltage)/100)) + '\nActual power supply voltage: ' + str((float(newValue)/100))
                           + '\nUUT might be drawing too much current.  Power supply current limit set to : ' + str(self.GetPsupplyUpperCurrent()))
            return [0, errorReport]
        
        #make sure power supply isn't in constant current mode.  Wait 1 sec after power is applied to check if in CC mode.
        #If in CC mode, UUT drawing too much current
        time.sleep(1)
        self.pSupplyCom.write('GETD\r')
        returnValue = self.TimeoutCheck(self.pSupplyCom, 'GETD')
        if (returnValue[1] != 'OK'):
            temp = self.TimeoutCheck(self.pSupplyCom, 'GETD')
            if not temp[0]:
                return [0, 'pSupply failed to return "OK" after CC mode status.']
        modeCheck = (int(returnValue[1]) & 1)#The CC mode bit is the last element of the psupply response string
        #010 represents 1V. The power supply interprets '125' as 12.5V and '008' as 800mV.  If the desired voltage is less than 1V,
        #then the power supply is off and will be in constant current mode.  The if statement prevents failing the test if this is the case
        if (int(desiredVoltage) > 10):
            if (modeCheck == 1):
                return [0, 'UUT drawing more than ' + str(self.GetPsupplyUpperCurrent()) + '.  Power supply entered into CC mode when power applied']
        
        return [1, '']

    def GetPsupplyCurrent(self):
        self.pSupplyCom.write('GETD\r')
        returnValue = self.TimeoutCheck(self.pSupplyCom, 'GETD')
        if (returnValue[1] != 'OK'):
            temp = self.TimeoutCheck(self.pSupplyCom, 'GETD')
            if not temp[0]:
                returnValue[1] = returnValue[1] + '\npSupply failed to return "OK" after CC mode status.'
                return [0, returnValue[1]]
        current = ''
        returnValue = returnValue[1]
        for i in range(4, 8, +1):
            current = current + returnValue[i]
        current = float(float(current)/1000) #move the decimal left to convert the power supply generic output to real current
        return [1, current]

