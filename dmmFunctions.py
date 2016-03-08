import serial
import time

class Dmm:
    
    dmmCom = None
    dmmComIsOpen = False

    def SetupComport(self, device):
        self.dmmCom = serial.Serial(device, baudrate=9600, timeout=1)        
        if self.dmmCom.isOpen():
            if not self.AssignComport():
                self.dmmCom.close()
                return 0
        else:
            #unable to open device as serial port
            return 0
        self.dmmComIsOpen = True
        return 1

    #Called from the setupDmmComport() function
    def AssignComport(self):                            
        self.dmmCom.write('*IDN?\n')
        tempString = self.dmmCom.readline()
        if '34401A' in tempString:
            self.dmmCom.write('system:remote\n')
            return 1                                    
        return 0

    #default function params 'def' allows dmm to automatically select the correct range
    #to request a resistance measurement, set measurementType to 'res' 
    def DmmMeasure(self, measurementType='volt:dc', dmmRange='def', dmmResolution='def'):
            reply = ''
            error = ''
            self.dmmCom.write('meas:' + measurementType + '? ' + dmmRange + ", " + dmmResolution + '\n')
            queryTime = time.time()
            reply = self.dmmCom.readline()    
            queryTime = time.time() - queryTime
            if not self.TimeoutCheck(queryTime, 'DmmMeasure()'):
                self.dmmCom.write('system:error?\n')
                error = self.dmmCom.readline()
                raise ValueError('dmm timeout')
            self.dmmCom.write('system:error?\n')
            error = self.dmmCom.readline()
            if 'No error' in error:
                return reply
            else:
                raise ValueError('dmm error')

    def TimeoutCheck(self, queryTime, taskName):
        #if read op. > 1 sec, generate prog. error
        if queryTime >= 1:
            return 0
        else:
            return 1
