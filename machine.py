#!/usr/bin/python3
# file: machine.py
# created = 17 january 2022
# modified: 30 january 2022
# author = Roch Schanen
 
#######################################################

fc = "./engine.cfg"

DBG = [
    # 'CONFIG',    'CONST',    'REGISTERS',    'LOAD',
    # 'PARSELINE',
    "opNOP",
    "opXFR",
    "opJMP",    "opJNZ",    "opJZE",
    "opADC",    "opSHR",    "opSHL",
    "opAND",    "opIOR",    "opEOR",
    ]

fp = "./code.machine"

#######################################################

from sys import argv

if len(argv)>1:
	fp = argv[1]        

fh = open(fp, 'r') 		# file handle
ft = fh.read() 			# file text
fh.close()

l0 = ft.split("\n", 1)[0] 	# first line
en = l0[2:]					# engine name

if en == "./engine__003.py": from engine.engine__003 import engine
if en == "./engine__004.py": from engine__004 import engine

# instanciate engine
EGN = engine(DBG, fc)
# load machine code
if EGN.load(ft):
	# run machine code
	EGN.processCode()
