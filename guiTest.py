from Tkinter import *

root = Tk()

li = 'list of something'.split()
listb = Listbox(root)
for item in li:
    listb.insert(0,item)

listb.pack()
root.mainloop()
