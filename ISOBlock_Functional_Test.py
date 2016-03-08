#!/usr/bin/env python

#To make this program executable from any directory:
#place the following string as the first line in this file: '#!/usr/bin/env python'
#Now, exectute the three following commands in a terminal window:
#1) chmod +x /home/pi/Python\ Projects/ISOBlock/ISOBlock_Functional_Test.py
#2) sudo cp /home/pi/Python\ Projects/ISOBlock/ISOBlock_Functional_Test.py /usr/local/bin/
#3) sudo mv /usr/local/bin/ISOBlock_Functional_Test.py /usr/local/bin/ISOBlock_Functional_Test

import sys

#When this module is exectuted, the below piece of code
#includes other references to python modules in the
#directory that they reside in normally
sys.path.insert(0, '/home/pi/Python Projects/ISOBlock')

import IsoBlockMain as Main

#Check equipment is connected
print 'Setting up test equipment, please wait ~5 seconds'
if not Main.SetupComports():
    Main.UpdateTextArea('\nUnable to set up test equipment.  '
                        'Check the test equipment connections '
                        'and be sure they are powered on.  You '
                        'must restart the test program to attempt '
                        'equipment setup again.')

Main.LoadGUI()
