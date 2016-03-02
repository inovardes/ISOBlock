import RPi.GPIO as GPIO

class ProgConst:
    #I2C Global
    I2C_ADDR = 0x1D
    
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
    ADC_CORRECTIONS = 14

    #RPi GPIO globals
    syncNotEnable = 8
    isoBlockEnable = 10
    rPiReset=12
    vinShuntEnable = 16
    vinKelvinEnable = 18
    voutShuntEnable = 22
    voutKelvinEnable = 24
    fanEnable = 26
    picEnable = 32
    picAutoProgramEnable = 36
    programmerStatus = 38
    i2c_SDA_Lynch = 11 #for pulling(Lynching) SDA line (disconnect from Slave)

    #Measurement & Tolerance Variables

    #UUT Vout Limits
    UUT_Vout_Off = 5.50 #5.50V
    UUT_Vout_Off_Low = .5 #500mV
    UUT_Vout_On = 8.50 #8.50V

    #Programming Limits
    programming_I_Limit = '002' #'001' = 100mA
    programming_V_Limit = '150' #'150' = 15V

    #Calibration Limits
    cal_V_Limit = '280' #'280' = 28V
    calMode_V_Limit = '125' #'125' = 12.5V

    #Initial power up limits
    initPwrUp_Psupply_V_Max = '280' #'280' = 28V
    initPwrUp_Psupply_I_Low = '001' #'001' = 100mA
    initPwrUp_Psupply_I_High = '010' #'010' = 1A
    Vin_initPwrUp_I_VoutOff_Limit = .020 #20mA
    initPwrUp_VoutOff_Limit = 5.50 #5.50V
    Vin_initPwrUp_I_VoutOn_Limit = .95 #95mA
    initPwrUp_VoutOn_Limit = 10.0 #10.0V
    initPwrUp_VoutOn_Toler = 1.50 #1.50V

    #Vout calibration limits
    voutCal_Psupply_I_Limit = '055' #'055' = 5.5A
    vout_cal_eload_I_Limit = 5.1 #5.1A
    vout_cal_eload_I_CCMode_Set = 5.0 #5A
    voutPostCal_V = 10.0 #10.0V
    voutPostCal_Toler = .200 #.05 #50mV

    #Vout current calibration Limits
    current_cal_eload_I_Limit = 12.6 #12.6A
    current_cal_eload_I_CCMode_Set = 12.5 #12.5A


    #Vin calibration
    vinCal_Psupply_I_Limit = '015' #'015' = 1.5A

    #Give UUT unique Serial#
    uutSerialNum_Psupply_I_Limit = '015' #'015' = 1.5A

    #Line load regulation limits
    lineRegCheck_Psupply_V_Low = '240' #'240' = 24.0V
    lineRegCheck_Psupply_V_Mid = '280' #'280' = 28.0V
    lineRegCheck_Psupply_V_High = '360' #'360'= 36.0V
    lineRegCheck_Psupply_I_Limit = '055' #'055' = 5.5A
    lineRegCheck_eload_I_Low_Limit = 0.0
    lineRegCheck_eload_I_Low_CCMode_Set = 0.0
    lineRegCheck_eload_I_Mid_Limit = 5.1
    lineRegCheck_eload_I_Mid_CCMode_Set = 5.0
    lineRegCheck_eload_I_High_Limit = 10.1
    lineRegCheck_eload_I_High_CCMode_Set = 10.0
    lineRegCheck_Vout_Limit = 10 # 10V
    lineRegCheck_Vout_I_Low_Toler = .05 #50mA
    lineRegCheck_Vout_I_Mid_Toler = .30 #300mA
    lineRegCheck_Vout_I_High_Toler = .50 #500mA

    synchPinPsupply_V = '280' #'280' = 28.0V
    synchPinPsupply_I = '010' #'010' = 1.0A
    

    def __init__(self):
        ###RPi GPIO setup
        GPIO.setwarnings(False) #Disbale the warnings related to GPIO.setup command: "RuntimeWarnings: This channel is already in use, continue anyway."
        GPIO.setmode(GPIO.BOARD) #Refer to RPi header pin# instead of Broadcom pin#
        GPIO.setup(self.syncNotEnable, GPIO.OUT)
        GPIO.setup(self.isoBlockEnable, GPIO.OUT)
        GPIO.setup(self.vinShuntEnable, GPIO.OUT)
        GPIO.setup(self.vinKelvinEnable, GPIO.OUT)
        GPIO.setup(self.voutShuntEnable, GPIO.OUT)
        GPIO.setup(self.voutKelvinEnable, GPIO.OUT)
        GPIO.setup(self.fanEnable, GPIO.OUT)
        GPIO.setup(self.picEnable, GPIO.OUT)
        GPIO.setup(self.picAutoProgramEnable, GPIO.OUT)
        GPIO.setup(self.programmerStatus, GPIO.IN)
        GPIO.setup(self.rPiReset, GPIO.OUT)        
        GPIO.setup(self.i2c_SDA_Lynch, GPIO.OUT)#for pulling(Lynching) SDA line up through 1K resistor to 5V
