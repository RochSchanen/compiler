#!/usr/bin/python3
# file: engine__003.py
# created = 11 September 2021
# modified: 30 January 2022
# author = Roch Schanen
 
"""
A simple but flexible core engine.
The code, stored in a string array,
is interpreted line by line. A first
pass determines labels and reserves
memory. This engine should emulate
our FPGA softcore processor coupled
with a standard static RAM.
"""

# standard modules
from sys import argv
from datetime import date

# local classes and functions

class config():

    def __init__(self, cd):
        self.cd = cd
        return

    def parsetext(self, text):
        # debug string
        ds = ""
        # parse
        L = text.split('\n')
        for l in L:
            if "=" in l:
                key, val = l.split('=', 1)
                if key.strip() in self.cd.keys():
                    s = val.strip()
                    x = self.cd[key.strip()]
                    if isinstance(x, int): n = int(s)
                    if isinstance(x, float): n = float(s)
                    if isinstance(x, str): n = s
                    ds += f'set {key.strip()} = {n}\n'
                    self.cd[key.strip()] = n
        # done
        return ds[:-1]

    def parsefile(self, name):
        fh = open(name)
        ft = fh.read()
        fh.close()
        return self.parsetext(ft)

# overide default options
def setDebugOtpions(dico, opts):
    for o in opts:
        if o in dico.keys():
            dico[o] = True
    return

# convert a character string
# to an integer value (no checks)
def strtoint(bs, base = 10):
    conversionTable = {
        '0':0,  '1':1,  '2':2,  '3':3,
        '4':4,  '5':5,  '6':6,  '7':7,
        '8':8,  '9':9,  'A':10, 'B':11,
        'C':12, 'D':13, 'E':14, 'F':15,
        }
    v, n = 0, len(bs)
    for i in range(n):
        v *= base 
        I = bs[i].upper()
        v += conversionTable[I]
    return v
 
# parse an unsigned integer number
def getuint(bs, p, base = 10):
    charSets = {
        2 :"01",
        8 :"01234567",
        10:"0123456789",
        16:"0123456789ABCDEF",
        }
    n = p
    while bs[n].upper() in charSets[base]: n += 1
    if n > p: return strtoint(bs[p:n], base), n
    return None, p
 
# get a single sign symbol
def getsign(bs, p):
    if bs[p] == "-": return True, p + 1
    if bs[p] == "+": return False, p + 1
    return False, p
 
# get a signed integer number
def getsint(bs, p, base = 10):
    s, n = getsign(bs, p)
    i, m = getuint(bs, n, base)
    if i is None: return None, p
    if s: return -i, m
    return i, m
 
# get signed integer including a base prefix
def getInt(bs, p):
    prefixSet = {
        "0X":16,
        "0D":10,
        "0O":8,
        "0B":2,
        }
    s, n = getsign(bs, p)
    b, cc, o = 10, bs[n:n+2].upper(), 0
    if cc in prefixSet: b, o = prefixSet[cc], 2
    v, m = getuint(bs, n+o, b)
    if s: return -v, m
    return v, m

# get an alphanumeric sequence
def getId(bs, p):
    # define characters sets
    A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    AN = A + "0123456789"
    # record start
    n = p
    # filter first character
    if not bs[n].upper() in A: return None, p
    # filter next charcters
    while bs[n].upper() in AN: n += 1
    # check for al least one valid char
    if n > p: return bs[p:n].upper(), n
    # no valid characters found (not an Id)
    return None, p

# skip space characters
# a hash character skips to the end of the string
# returns False if no space character is found
def skipSpaces(bs, p):
    S = " " + "\t"
    n = p
    # skip spaces
    while bs[n] in S: n += 1
    # check for comment
    if bs[n] == "#": return True, len(bs)-1
    # return valid spaces
    if n > p: return True, n
    # no valid space found
    return False, p

# skip spaces and check for end-of-string
def EndOfString(bs, p):
    t, p = skipSpaces(bs, p)
    return bs[p] == "\0"

# get an alphanumeric sequence + colon
def getLabel(bs, p):
    i, n = getId(bs, p)
    if i is None: return None, p
    # label is Id immediately followed by ":"
    if bs[n] ==":": return i, n+1
    return None, p

def getString(s, p):
    # check for opening quote
    if not s[p] == '"': return None, p
    # reach next char
    n = p+1
    # loop until closing quote
    while not s[n] in ['"','\0']: n += 1
    # no quote found
    if not s[n] == '"': return None, p
    # found valid string
    return s[p+1:n], n+1

def getintlist(s, p):
    # setup loop
    e, c, n = True, [], p
    # loop while separators are founcontentd
    while e:
        # get next integer
        t, n = getInt(s, n)
        # check for parse failure
        if t is None: return None, p
        # append new integer
        c.append(t)
        # reach next element
        t, n = skipSpaces(s, n)
        # integers are separted by commas
        if not s[n] == ",": break
        # skip comma
        t, n = skipSpaces(s, n+1)
    # done
    return c, n

# note the single function change
# compared with getintlist. this lists
# concept could be generalised
def getidlist(s, p):
    # setup loop
    e, c, n = True, [], p
    # loop while separators are founcontentd
    while e:
        # get next integer
        t, n = getId(s, n)
        # check for parse failure
        if t is None: return None, p
        # append new integer
        c.append(t)
        # reach next element
        t, n = skipSpaces(s, n)
        # integers are separted by commas
        if not s[n] == ",": break
        # skip comma
        t, n = skipSpaces(s, n+1)
    # done
    return c, n

# the main class

class engine():

# ---- ---- ---- ---- debug

    # debug enable defaults

    DBG = {

        # system
        'NOC'       : False,
        'LOAD'      : False,
        'CONST'     : False,
        'CONFIG'    : False,
        'REGISTERS' : False,
        'PARSELINE' : False,

        # no operations
        'opNOP'     : False,

        # jump opcodes
        'opJMP'     : False,
        'opJNZ'     : False,
        'opJZE'     : False,

        # transfers
        'opXFR'     : False,

        # arithmetics
        'opADC'     : False,
        'opSHR'     : False,
        'opSHL'     : False,

        # logic
        'opAND'     : False,
        'opIOR'     : False,
        'opEOR'     : False,
    }

# ---- ---- ---- ---- configuration

    """ 
    Defaults configuration parameters with their
    default values. The Default values are used
    also to define the parameters type.
    """

    CFG = {
        'VERSION'   :'0.04',
        'BITS'      : 0,
        'LOGFILE'   : '',
        'CYCLEMAX'  : 0,
        'REGS'      : ''
    }

# ---- ---- ---- ---- constants

    """ Constants are defined on creation (__init__).
    They must remain fixed after instance creation.
    """

    CB, MSB, MSK, LSB = None, None, None, 1

    # constructor
    
    def __init__(self, DEBUG = [], CONFIG = "./engine.cfg"):

        # setup debug options
        setDebugOtpions(self.DBG, DEBUG)

        # configure
        ch = config(self.CFG)
        ds = ch.parsefile(CONFIG)

        # open log file
        self.lh = open(self.CFG['LOGFILE'], 'w')
        self.log(f'# file: {self.CFG["LOGFILE"]}')
        self.log(f'# created: {date.today().strftime("%d %B %Y")}')
        self.log(f'# author: {argv[0].split("/")[-1]}')

        # log start up
        self.log(f"\nengine version {self.CFG['VERSION']}")

        # delayed log of the configuration parameters
        if self.DBG['CONFIG']:
            self.log(f"\nConfiguration:")
            self.log(ds)

        # set constants
        self.CB = 1<<self.CFG['BITS']
        self.MSK, self.MSB = self.CB-1, self.CB>>1

        # get extra registers
        if self.CFG['REGS']:
            R, n = getidlist(self.CFG['REGS']+'\0', 0)
            for r in R:
                if not r.upper() in self.REGS:
                    self.REGS[r.upper()] = 0

        if self.DBG['REGISTERS']:
            self.log(f"\nRegisters:")
            for r in self.REGS.keys():
                self.log(
                    f"{r:8} = " \
                    f"0b{self.REGS[r]:0{self.CFG['BITS']}b}")

        # log CONSTANTS
        if self.DBG['CONST']:
            w = self.CFG["BITS"]
            self.log(f"\nConstants:")
            self.log(f'CYCLEMAX  = d  {self.CFG["CYCLEMAX"]:{w}d}')
            self.log(f'BITS      = d  {w:{w}d}')
            self.log(f'CB        = b {self.CB:0{w}b}')
            self.log(f'MSK       = b  {self.MSK:0{w}b}')
            self.log(f'MSB       = b  {self.MSB:0{w}b}')
            self.log(f'LSB       = b  {self.LSB:0{w}b}')
            self.log("")            

        # done
        return

    # destructor
    
    def __del__(self):
        # close log
        self.lh.close()
        # done
        return
 
    # log

    def log(self, logstr, end = "\n"):
        # display
        print(logstr, end = end)
        # log
        self.lh.write(f"{str(logstr)}{end}")
        # done
        return

# ---- ---- ---- ---- registers

    # define default registers
    
    REGS = {
        "STATUS":   0b00000000,
        "R0":       0b00000000,
        }

# ---- ---- ---- ---- flags

    # define each flag bit and its weight

    FLAGS = {
        "N": 0b1000, # "Negative sign" bit
        "Z": 0b0100, # "zero" bit
        "O": 0b0010, # "overflow" bit
        "C": 0b0001, # "carry" bit
    }

    # raise status register flags

    def raiseFlags(self, names):
        for n in names:
            self.REGS["STATUS"] |= self.FLAGS[n]
        return

    # lower status register flags
    
    def lowerFlags(self, names):
        for n in names:
            self.REGS["STATUS"] &= ~self.FLAGS[n]
        return

    # update Z and N flag from register

    def updateZN(self, r):
        self.lowerFlags("ZN")
        if r == 0: self.raiseFlags("Z")
        if r & self.MSB > 0: self.raiseFlags("N")
        return

# ---- ---- ---- ---- formating

    # status register formating function

    def statregfm(self, k):
        s, r = "", self.REGS[k]
        for f in self.FLAGS.keys():
            s += f if r & self.FLAGS[f] else "."
        return s

    # special registers formating functions
    
    REGFM = {
        "STATUS": statregfm,
    }

    # any register formatting
    
    def regfm(self, r):
        if r in self.REGFM.keys():
            return f"{r}:{self.REGFM[r](self, r)}"
        return f"{r}:{self.usfm(self.REGS[r])}"

    # unsigned(signed) value formatting
    
    def usfm(self, x):
        sx = x & self.MSB > 0 
        xs = x - self.CB if sx else x
        # returns unsigned and signed value of x
        return f"{x}:{xs}"

# ---- ---- ---- ---- lists and dicts

    il = []     # instructions list
    ll = {}     # labels list
    ml = {}     # memory references
    MM = []     # memory storage

# ---- ---- ---- ---- PARSING METHODS

    # pointer to char fail
    def parseFail(self, s, p, ip = None):
        msg = s.replace("\0", "\\0")
        msg = f"{msg}\n{p*'.'}^{(len(s)-p-1)*'.'}"
        return msg

    # parse a line without interpretation
    # split label from opcode from arguments    
    def parseLine(self, s, i = None):
        # log tab length
        TAB = 4
        # debug flag
        dl = self.DBG['PARSELINE']
        # fix empty string
        if not s: s = "\0"
        # fix end-of-line terminaison
        if s[-1] != "\0": s += "\0"
        # log string to parse
        if dl:
            msg = s[:-1].replace(" ", "\u2591")
            msg = f'PARSE: "{msg}\\0"'
            if i is not None:
                msg = f'{i:6} {msg}'
        # skip heading spaces
        t, n = skipSpaces(s, 0)
        # test empty line (no label, implicit nop, no args)
        if s[n] == "\0":
            if dl & self.DBG['NOC']:
                self.log(f"\n{msg}")
                self.log(f"{'-':>8} opcode: 'NOC'")
            return "", "NOC", "\0"
        # check for label
        lbl, n = getLabel(s, n)
        # reach the opcode
        t, n = skipSpaces(s, n)
        # check no opcode (label, implicit nop, no args)
        if s[n] == "\0":
            if dl & self.DBG['NOC']:
                self.log(f"\n{msg}")
                self.log(f"{'-':>8} opcode: 'NOC'")
            return lbl, "NOC", "\0"
        # get the opcode
        opc, p = getId(s, n)
        # opcode fail 
        if opc is None:
            return None, f"FAIL", self.parseFail(s, n, i)
        if not opc in self.OPCODES.keys():
            return None, f"FAIL", self.parseFail(s, n, i)
        # log
        if dl:
            self.log(f"\n{msg}")
            self.log(f"{'-':>6} opcode:'{opc}'")
        # skip spaces to reached arguments
        t, n = skipSpaces(s, p)
        # collect arguments
        args = s[n:]
        # done
        return lbl, opc, args

    def getReference(self, s, p):
        r, n = getId(s, p)
        # check reference list
        if r in self.ll.keys():
            return r, n
        return None, p

    def getRegister(self, s, p):
        r, n = getId(s, p)
        # check registers list
        if r in self.REGS.keys():
            return r, n
        return None, p

    def getRegisterList(self, s, p):
        # setup loop
        e, R, n = True, [], p
        # loop until no comma is found
        while e:
            # get next register
            r, n = self.getRegister(s, n)
            # no register found: fail
            if r is None: return None, p
            t, n = skipSpaces(s, n)
            # append register
            R.append(r)
            # registers are separted by commas
            if not s[n] == ",": break
            t, n = skipSpaces(s, n+1)
        # done
        return R, n

    def getrefsrc(self, s, p):
        fail = None, p, ""
        # get reference
        r, n = self.getReference(s, p)
        if r is None: return fail
        # line pointer
        if not r in self.ml.keys():
            # init vars
            v = self.ll[r] # value
            m = f"{r}:{v}" # message
            # check for word filter
            t, k = skipSpaces(s, n)
            if s[k] == "$":
                # skip spaces and get integer
                i, k = getInt(s, k+1)
                # check fail
                if i is None: return fail
                # continue
                j = i * self.CFG["BITS"]
                n, v, m = k, (v >> j) & self.MSK, f"{m} ${i}"
            return v, n, m
        # memory pointer
        # init vars
        v = self.ml[r] # value
        m = f"{r}:{v}" # message
        # check for offset
        t, k = skipSpaces(s, n)
        if s[k] == "+":
            # skip spaces and get integer
            t, k = skipSpaces(s, k+1)
            i, k = getInt(s, k)
            # check fail
            if i is None: return fail
            # continue
            n, v, m = k, v + i, f"({m}+{i}):{v+i}"
        # check for word filter
        t, k = skipSpaces(s, n)
        if s[k] == "$":
            # skip spaces and get integer
            i, k = getInt(s, k+1)
            # check fail
            if i is None: return fail
            # continue
            j = i * self.CFG["BITS"]
            n, v, m = k, (v >> j) & self.MSK, f"{m} ${i}"
        return v, n, m

    def parseMemoryAddress(self, s, p, db):
        # check for registers
        R, n = self.getRegisterList(s, p)
        if R is not None:
            # compute address and message
            adr, wgt, msg = 0, 1, ""
            for r in R:
                # add register value with weight
                adr += self.REGS[r]*wgt
                # increase weight
                wgt *= self.CB
                # pad message
                msg += f"{r}:{self.REGS[r]}, "
            # done
            return adr & self.AWM, n, msg[:-2]
        # fail to parse if no DOUBLEACCESS
        if not db: return None, p, ""
        # check for integer
        i, n = getInt(s, p)
        # done
        if i is not None:
            return i & self.AWM, n, f"{i}"
        # check for reference
        adr, n, m = self.getrefsrc(s, p)
        # done
        if adr is not None:
            return adr, n, m
        # failed to parse
        return None, p, ""

    def getMemoryAddress(self, s, p, db = False):
        fail = None, p, ""
        # check opening bracket
        if not s[p] == "[":
            return fail
        # parse address
        t, n = skipSpaces(s, p+1)
        adr, n, msg = self.parseMemoryAddress(s, n, db)
        if adr is None: return fail
        # check closing bracket
        t, n = skipSpaces(s, n)
        if not s[n] == "]":
            return fail
        # done
        return adr, n+1, f"[{msg}]"

    def getregsrc(self, args):
        fail = None, None, ""
        # get destination register
        d, n = self.getRegister(args, 0)
        if d is not None:
            t, n = skipSpaces(args, n)
            # source is integer
            s, n = getInt(args, n)
            if s is not None:
                # coerce to bit width
                v = s & self.MSK
                if EndOfString(args, n):
                    return d, v, f"{v}"
                return fail
            # source is reference
            v, n, m =self.getrefsrc(args, n)
            if v is not None:
                if EndOfString(args, n):
                    return d, v, m
            # source is register
            s, n = self.getRegister(args, n)
            if s is not None:
                # get register value
                v = self.REGS[s]
                if EndOfString(args, n):
                    return d, v, f'{s}:{v}'
                return fail
            # source is memory
            s, n, m = self.getMemoryAddress(args, n)
            if s is not None:
                # get memory value
                v = self.MM[s]                
                if EndOfString(args, n):
                    return d, v, f'{m}:{v}'
                return fail
        # parse fail
        return fail

    def getmemsrc(self, args):
        fail = None, 0, ""
        # get destination memorylabels list
        d, n, m = self.getMemoryAddress(args, 0)
        if d is None: return fail
        t, n = skipSpaces(args, n)
        # source must be register
        s, n = self.getRegister(args, n)
        if s is None: return fail
        if EndOfString(args, n):
            return d, s, m
        # parse fail
        return fail

    def getContent(self, s, p, i):
        # try string content
        c, n = getString(s, p)
        if c is not None:
            # check data length
            l = len(c)
            if l > i:
                self.log(
                    "error: string length is " \
                    "larger than allocated memory.")
                return None, p
            # right pading with spaces
            # c += (i-l) * " "
            # right pading with zeroes
            c += (i-l) * "\0"
            # return integer arraylabels list
            return [(ord(x) & self.MSK) for x in c], n
        # try integer list
        c, n = getintlist(s, p)
        if c is not None:
            # check data length
            l = len(c)
            if l > i:
                self.log(
                    "error: integer list length is " \
                    "larger than allocated memory.")
                return None, p
            # right paddding with zeros
            c += (i-l)*[0]
            # return integer array
            return [(x & self.MSK) for x in c], n
        # parse fail
        return None, p

# ---- ---- ---- ---- control codes

    # no code

    def opNOC(self, args, ip, cc, header = ""):
        # self.log(f"{header}noc")
        return True, ip+1, cc

    # allocate memory (run-time error)
    
    def opMEM(self, args, ip, cc, header = ""):
        self.log(
            f"{header}MEM error: " \
            f"MEM is not an executable instruction")
        return False, ip+1, cc

    # display/log register/memory
    
    def opDSP(self, args, ip, cc, header = ""):
        # check for register
        s, n = self.getRegister(args, 0)
        if s is not None:
            self.log(f'{header}{self.regfm(s)}')
            return EndOfString(args, n), ip+1, cc
        # check for memory
        s, n, m = self.getMemoryAddress(args, 0, True)
        if s is not None:
            v = self.MM[s]
            self.log(f'{header}{m}:{self.usfm(v)}')
            return EndOfString(args, n), ip+1, cc
        # parsing failed
        self.log(f'{header} DSP error: invalid argument')
        # done
        return False, ip+1, cc

# ---- ---- ---- ---- Null Operation

    # one cycle delay

    def opNOP(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opNOP']
        # check number of parameters
        if not args == '\0':
            self.log(f"NOP error: no argument expected")
            return False, ip, cc 
        # log
        if dl: self.log(f"{header}NOP")
        # done
        return True, ip+1, cc+1

# ---- ---- ---- ---- jump opcodes

    # general jump method
    def opJMP(self, args, ip, cc, header = "", 
            op = "JMP", condition = True):
        # init vars
        dl, adr, msg = self.DBG[f'op{op}'], None, None

        # check for "register list" parameter
        R, n = self.getRegisterList(args, 0)
        if R is not None:
            # check end of line
            if not EndOfString(args, n):
                self.log(f'{header}{op} error: parsing failed')
                return False, ip+1, cc
            # computer line address
            adr, wgt, msg = 0, 1, "["
            for r in R:
                # add register value with weight
                adr += self.REGS[r]*wgt
                # increase weight
                wgt *= self.CB
                # update message
                msg = f"{msg}{r}, "
            # close bracket
            msg = f"{msg[:-2]}]"
        # check for "constant" parameter
        r, n = self.getReference(args, 0)
        if r is not None:
            # check end of line
            if not EndOfString(args, n):
                self.log(f'{header}{op} error: parsing failed')
                return False, ip+1, cc
            adr, msg = self.ll[r], r
        # branch: jump or continue
        if adr is not None:
            # jump
            if condition:
                if dl: self.log(f"{header}{op} to {msg}:{adr}")
                return True, adr, cc+1
            # continue
            else:
                if dl: self.log(f"{header}{op} continue")
                return True, ip+1, cc+1
        # fail parse
        self.log(f'{header}{op} error: parsing failed')
        return False, ip+1, cc

    # jump if zero (Z set)
    def opJZE(self, args, ip, cc, header = ""):
        Z = self.REGS["STATUS"]  & self.FLAGS["Z"] > 0
        return self.opJMP(args, ip, cc, header, "JZE", Z)

    # jump if non zero (Z clear)
    def opJNZ(self, args, ip, cc, header = ""):
        Z = self.REGS["STATUS"]  & self.FLAGS["Z"] > 0
        return self.opJMP(args, ip, cc, header, "JNZ", not Z)

# ---- ---- ---- ---- transfer opcodes

    def opXFR(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opXFR']
        # destination is register
        r, v, m = self.getregsrc(args)
        if r is not None:
            # transfert
            self.REGS[r] = v
            # log
            if dl: self.log(
                f"{header}{r} = " \
                f"{m} = " \
                f"{self.usfm(v)}")
            return True, ip+1, cc+1
        # destination is memory
        d, s, m = self.getmemsrc(args)
        if d is not None:
            self.MM[d] = self.REGS[s]
            # done
            if dl: self.log(
                f"{header}{m} = " \
                f"{s}:{self.REGS[s]} = " \
                f"{self.usfm(self.REGS[s])}")
            return True, ip+1, cc+1
        # fail parse
        self.log(f'{header}XFR error: parsing failed')
        return False, ip+1, cc

# ---- ---- ---- ---- arithmetic opcodes

    # sum

    def opADC(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opADC']
        # retrieve accumulator and operand 
        regdest, value, msg = self.getregsrc(args)
        if regdest is None:
            return False, ip+1, cc
        # record values
        x, y = self.REGS[regdest], value
        # get input carry
        cin = self.REGS['STATUS'] & self.FLAGS['C'] > 0
        # perform operation
        z = x + y + [0, 1][cin]
        msg += [" + C:0", " + C:1"][cin]
        # compute signs from sign bits
        sx = x & self.MSB > 0
        sy = y & self.MSB > 0
        sz = z & self.MSB > 0
        # clear overflow and carry
        self.lowerFlags("OC")
        # update overflow
        O = (sx & sy & ~sz) | (~sx & ~sy & sz)
        if O: self.raiseFlags("O")
        # update carry
        C = z & self.CB > 0
        if C: self.raiseFlags("C")
        # coerce to bits size
        z &= self.MSK
        # update other flags
        self.updateZN(z)
        # update destination register
        self.REGS[regdest] = z
        # done
        if dl: self.log(
            f'{header}{regdest} = ' \
            f'{regdest}:{x} + {msg} = {self.usfm(z)}')
        return True, ip+1, cc+1

    # shift right

    def opSHR(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opSHR']
        # get the destination/source register
        regdest, n = self.getRegister(args, 0)
        if regdest is None:
            return False, ip+1, cc
        # record value
        x = self.REGS[regdest]
        # get carry and clear
        C = self.REGS["STATUS"] & self.FLAGS["C"] > 0
        self.lowerFlags("C")
        # get output bit
        D = x & self.LSB > 0
        # perform operation
        z = x >> 1
        # insert carry
        if C: z += self.MSB
        # update Carry and other flags
        if D: self.raiseFlags("C")
        self.updateZN(z)
        # update destination
        self.REGS[regdest] = z
        # log
        if dl:
            cs = [f"+ C:{0}", f"+ C:{self.MSB}"][C]
            self.log(
                f'{header}{regdest} = ' \
                f'>> {regdest}:{x} {cs} = '\
                f'{self.usfm(z)}')
        # done
        return True, ip+1, cc+1

    # shift left

    def opSHL(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opSHL']
        # get the destination/source register
        regdest, n = self.getRegister(args, 0)
        if regdest is None:
            return False, ip+1, cc
        # record value
        x = self.REGS[regdest]
        # get carry and clear
        C = self.REGS["STATUS"] & self.FLAGS["C"] > 0
        self.lowerFlags("C")
        # get output bit
        D = x & self.MSB > 0
        # perform operation
        z = x << 1
        # coerce to bits size
        z &= self.MSK
        # insert carry
        if C: z += self.LSB
        # update Carry and other flags
        if D: self.raiseFlags("C")
        self.updateZN(z)
        # update destination
        self.REGS[regdest] = z
        # done
        if dl:
            cs = [f"+ C:{0}", f"+ C:{self.LSB}"][C]
            self.log(
                f'{header}{regdest} = ' \
                f'<< {regdest}:{x} {cs} = ' \
                f'{self.usfm(z)}')
        return True, ip+1, cc+1

# ---- ---- ---- ---- logic opcodes

    # logic AND

    def opAND(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opAND']
        # retrieve accumulator and operand 
        regdest, value, msg = self.getregsrc(args)
        if regdest is None:
            return False, ip+1, cc
        # record values
        x, y = self.REGS[regdest], value
        # perform operation
        z = x & y
        # update flags
        self.updateZN(z)
        # update destination register
        self.REGS[regdest] = z
        # done
        if dl: self.log(
            f'{header}{regdest} = ' \
            f'{regdest}:{x} & {msg} = {self.usfm(z)}')
        return True, ip+1, cc+1

    # inclusive OR

    def opIOR(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opIOR']
        # retrieve accumulator and operand 
        regdest, value, msg = self.getregsrc(args)
        if regdest is None:
            return False, ip+1, cc
        # record values
        x, y = self.REGS[regdest], value
        # perform operation
        z = x | y
        # update flags
        self.updateZN(z)
        # update destination register
        self.REGS[regdest] = z
        # done
        if dl: self.log(
            f'{header}{regdest} = ' \
            f'{regdest}:{x} v {msg} = {self.usfm(z)}')
        return True, ip+1, cc+1

    # exclusive OR

    def opEOR(self, args, ip, cc, header = ""):
        # debug flag
        dl = self.DBG['opEOR']
        # retrieve accumulator and operand 
        regdest, value, msg = self.getregsrc(args)
        if regdest is None:
            return False, ip+1, cc
        # record values
        x, y = self.REGS[regdest], value
        # perform operation
        z = x ^ y
        # update flags
        self.updateZN(z)
        # update destination register
        self.REGS[regdest] = z
        # done
        if dl: self.log(
            f'{header}{regdest} = ' \
            f'{regdest}:{x} ^ {msg} = {self.usfm(z)}')
        return True, ip+1, cc+1

# ---- ---- ---- ---- opcode names definition

    OPCODES = {
        "NOC": opNOC, "MEM": opMEM, "DSP": opDSP,  # control codes
        "NOP": opNOP,                              # no operation
        "XFR": opXFR,                              # transfer
        "ADC": opADC, "SHR": opSHR, "SHL": opSHL,  # arithmetics
        "AND": opAND, "IOR": opIOR, "EOR": opEOR,  # logic
        "JMP": opJMP, "JNZ": opJNZ, "JZE": opJZE,  # flow
        }

# ---- ---- ---- ---- load

    # the first pass (no execution)
    # collect labels (setup pointers)

    def load(self, s):
        # debug flag
        dl = self.DBG['LOAD']
        if dl: self.log("load code:")
        # append to list of instructions
        self.il += s.split("\n")
        # add dummy first line to fix line sync with editor
        self.il.insert(0,"")
        # collect all references in one pass
        for i, s in enumerate(self.il[1:]):
            # parse
            lbl, opc, args = self.parseLine(s, i)
            # exit on failure
            if opc == "FAIL":
                self.log(f"\nparse error while loading code.")
                self.log(f"failed to parse opcode at line {i}.")
                self.log(f"{args}")
                self.log(f"exiting...")
                return False
            # no label
            if not lbl: continue
            # check for existing reference
            if lbl in self.ll.keys():
                self.log(
                    f"Duplicate reference '{lbl}' " \
                    f"at lines {self.ll[lbl]} & {i}")
                return False
            # add label to reference list
            if dl: 
                self.log(f"{'-':>6} new label '{lbl}'", end = "")
                self.log(f" at line {i}")
            self.ll[lbl] = i
            # check for special opcode MEM
            if opc == "MEM":
                # allocate
                if not self.allocate(lbl, args):
                    self.log("allocation failed")
                    return False
                # done
                continue
        # compute address width and mask
        w, l = 0, len(self.MM)-1
        # prevent infinite loop when memory size is null
        if l < 0: l = 0
        # compute width
        while l: w, l = w+1, l>>1
        # get mask
        self.AWM = 2**w-1
        # display summery
        if dl: 
            self.log("\nsummary:")
            self.log(f" recorded {len(self.ll)} label(s)")
            self.log(f" recorded {len(self.ml)} address(es)")
            self.log(f" full memory size is {len(self.MM)}")
            self.log(f" address width is {w}")
            self.log(f" address mask is {self.AWM}")
        # done
        return True

    # allocate memory
    def allocate(self, lbl, args):
        # debug flag
        dl = self.DBG['LOAD']
        # look for an integer value
        i, n = getInt(args, 0)
        # parse failed
        if i is None:
            self.log(
                "MEM error: allocation length" \
                " undefined, integer expected")
            return False
        # check boundary
        if i < 1:
            self.log(
                "MEM error: allocation length" \
                " should be strictly positive")
            return False
        # reach for next argument
        t, n = skipSpaces(args, n)
        # create default array
        c = [0]*i # zero set
        # c = list(range(i)) # linear set
        # make the option random set
        # check for explicit content
        if args[n] == "=":
            # reach for next argument
            t, n = skipSpaces(args, n+1)
            # parse memory content
            c, n = self.getContent(args, n, i)
            # reach for next argument
            t, n = skipSpaces(args, n)
        # verify end of args
        if not args[n] == '\0':
            self.log(
                "MEM error: failed to parse," \
                " end of string expected")
            return False
        # record new memory address
        self.ml[lbl] = len(self.MM)
        # log
        if dl: self.log(
            f" new pointer '{lbl}' at address " \
            f"{self.ml[lbl]}:")
        # allocate memory
        self.MM.extend(c)
        # log
        if dl:
            # format memory value
            def fmv(i):
                # return f"{i:03}"
                return f"{i:3}"
                # return f"{i}"
            # tab
            tab = 2 * " "
            # display comment
            self.log(f" allocate + {i}:")
            # display memory array
            r = tab
            for i in c:
                # check maximum width
                if len(r) > 32:
                    # log
                    self.log(r)
                    # re-start
                    r = f"{tab}{fmv(i)},"
                else:
                    # continue: append
                    r += f"{fmv(i)},"
            # last part
            self.log(f"{r[:-1]}")        
        # done
        return True

# ---- ---- ---- ---- engine processor

    # process lines one by one (first pass required using load)
    def processCode(self):
        # cycles
        cc, cm = 0, self.CFG['CYCLEMAX']
        # instruction pointer
        r, ip = True, 0
        # formats
        t = f"{'':2}"
        # display
        self.log(f"\nstart processing:")
        self.log(f" line{t}cycles{t}instruction")
        self.log(f" ----{t}------{t}-----------")
        # while successfull, continue processing
        while r:
            # label and opcode already checked during loading
            lbl, opc, args = self.parseLine(self.il[ip], ip)
            # header
            h = f" {ip:04}{t}{cc:06}{t}"
            # execute and display
            r, ip, cc = self.OPCODES[opc](self, args, ip, cc, h)
            # interupt on failure
            if not r:
                self.log(f"error while running code at line {ip-1}.")
                self.log(f"exiting...")
                return
            # break on last instruction
            if ip == len(self.il):
                self.log(f"\nreached end of code.")
                r = False 
            # break on limit reached
            if cm:
                if cc > cm:
                    self.log(f"\n\nreached end of cycles.")
                    r = False
        # done
        return

if __name__ == "__main__":

    from os import system
    # default test code
    fp = "./code.machine"
    # alternative code
    if len(argv)>1: fp = argv[1]
    # execute root script         
    system(f"./machine.py {fp}")
    # execute tests


# TODO

"""

- write a test code to check all basic grammar.

- add display options: message string, tron, trof

- add default memory filling option in configuration file

- check systematically EndOfString parsing.

- improve parsing errors ouput infos

- import/export memory from/to file

- you cannot imput file during execution but
you can merge several files during loading:
add extra headers (file name?) to labels

- how to use flag bits values: use flag
names in syntax: define new syntax.

"""
