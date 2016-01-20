#Being new to Python, I'm under the impression function prototypes aren't used.
#I prefer not to search through a bunch of functions at the top of the file
#in search of the main program
#So this program simply calls the main program to allow a more 'C'-like syntax

import isoBlockProgramFunctions as Func

#Ensure equipment is connected
if not Func.SetupComports():    
    print 'unable to communicate with test equipment'
    sys.exit()
    
Func.MainWindow()

   
