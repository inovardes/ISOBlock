import isoBlockProgramFunctions as Func




#Ensure equipment is connected
if not Func.SetupComports():    
    print 'unable to communicate with test equipment'
    sys.exit()

Func.CreateGUI()
