from smbus import SMBus #library for I2C communication
import time
import sys
import RPi.GPIO as GPIO
import numpy as np
import isoBlockProgramFunctions as Func

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

# Main loop
#while True:

#Get the current system date and time
datetime = time.strftime('%m/%d/%Y %H:%M:%S')

#************************************************************
#general testing area.  Delete when finished
#************************************************************

#Ensure equipment is connected
if not Func.SetupComports():    
    #exit program
    print 'unable to connect all the test equipment'
    CloseProgram()
    sys.exit()
print 'read register values from Arduino:'
calRoutineCmd = bus.read_i2c_block_data(ADDR, 189, 6)
print(calRoutineCmd)
print(np.asarray(calRoutineCmd))
#bus.write_i2c_block_data(ADDR, 0x00, np.asarray(calRoutineCmd))


#dmmThread = threading.Thread(name='dmmThread', target=Func.dmmMeasure, args=(15,))

try:
    dmmMeasurement = ''
    dmmMeasurement = Func.dmmMeasure()


    
except ValueError, err:
    print 'exception response in main program: '
    print err
    for index in range(len(Func.testErrorList)):
        print Func.testErrorList[index]


        
print('DMM measurement: ' + dmmMeasurement)

##Func.ProgramPic()
##Func.PSupplyCommand()
##Func.PSupplyQuery()
##Func.TalkToIsoBlock(0x93)
##Func.EloadCommand()
##Func.EloadQuery()

GPIO.output(syncNotEnable, 0)
time.sleep(1)
GPIO.output(syncNotEnable, 1)
#************************************************************
#Program begins here
#************************************************************
#connect the PIC programmer by enabling picEnable

GPIO.cleanup()
Func.CloseProgram()
#Program ends here



    
