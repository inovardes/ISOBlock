import isoBlockProgramFunctions as Func

#Ensure equipment is connected
if not Func.SetupComports():    
    print 'unable to communicate with test equipment'
    Func.EndProgram()
    Func.GPIO.cleanup
    sys.exit()

Func.LoadGUI()
