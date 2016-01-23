#Called from the SetupComports() function
def AssignDMMComport(comportList):
    global dmmCom
    global dmmComIsOpen
    #open each comport in comportList and see if the Agilent, model 34401A, responds
    #if it responds, the respective comport will be removed from the comportList
    
        else:            
                            
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
            
                
    return 0

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
                elif (not eLoadComIsOpen) and AssignEloadComport(tempDevice):
                    eLoadCom = tempDevice
                    eLoadComIsOpen = True
                elif (not pSupplyComIsOpen) and AssignPsupplyComport(tempDevice)
                    pSupplyCom = tempDevice
                    pSupplyComIsOpen = True
                else:
                    UpdateTextArea('Unable to talk to any test equipment using: ' + comportList)
            else:
                UpdateTextArea( 'Unable to open comport: ' + comportList[index] + '\n')
        except:
            UpdateTextArea('Exception occurred while setting up comport: ' + tempDevice + ' in the "AssignDMMComport" function')
    if pSupplyComIsOpen and eLoadComIsOpen and dmmComIsOpen:
        return 1
    else:
        UpdateTextArea('Unable to communicate with some test equipment: \n'
                       'DMM = ' + dmmComIsOpent + 'Electronic Load = ' +
                       eLoadComIsOpen + 'Power Supply = ' + pSupplyComIsOpen)
        dmmComIsOpen = False
        eLoadComIsOpen = False
        pSupplyComIsOpen = False
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
