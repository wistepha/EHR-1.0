#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from USBInterface_libftd2xx import USBInterface
    #from USBInterface_libftdi import USBInterface
    #from USBInterface_pyftdi import USBInterface
except ImportError:
    print "failed to import USBInterface_libXYZ"
    print "check PYTHONPATH "
    exit(1)
    
import time, os, sys
import argparse
import struct
from collections import OrderedDict
import random
        

#conversions, see psi46tb.cc http://docs.python.org/2/library/struct.html
def LONG(value):    return struct.pack('l',value)
def ULONG(value):   return struct.pack('L',value)
def SHORT(value):   return struct.pack('h',value)
def USHORT(value):  return struct.pack('H',value)
def UCHAR(value):   return struct.pack('B',value)



########################################################################
class StringR(object):
    """ mutable string container for emulating 
        C++'s pass-by-reference idiom which is used for RPC calls
    """
########################################################################
    def __init__(self, value=""):
        self.value=value
    def __str__(self):
        if self.value is None:
            return "None"
        return self.value
########################################################################


########################################################################
class IntR(object):
    """ mutable integer, quite limited, don't use assignment operators
    inside called functions, only +=, -= and set. Access the value
    using int() """
########################################################################
    def __init__(self, value=0):
        self.value=value
    def set(self, value): self.value=value
    def __int__(self):   return self.value
    def __add__(self, y): self.value+=y
    def __sum__(self, y): self.value-=y
########################################################################







########################################################################
class RPC(object):
    """ callable objects that become the rpc stubs of the DTB object 
        argument values of the most recent call are chached and 
        can be retrieved with the getarg() method (useful for rocId)
    """
########################################################################
    DEBUG=False

    SIMPLE=-1
    REFERENCE = 0
    VECTOR = 1
    VECTORR = 2
    STRING = 3
    STRINGR = 4
    HWVECTORR = 5
    TYPES={ "v": (0, " "),  # {Beats type indicator: (bytes, python/C format)}
            "b": (1, "B"),  # bool transmitted as uint8_t, see PUT_BOOL in rpc.h
            "c": (1, "b"), 
            "C": (1, "B"),  # uint8
            "s": (2, "h"),
            "S": (2, "H"),  # unsigned short / uint16_t
            "i": (4, "i"),
            "I": (4, "I"),
            "l": (8, "l"),
            "L": (8, "L") }
    TYPE_DTB      = 0xC0
    TYPE_DTB_DATA1 = 0xC1  # firmware 1.x
    TYPE_DTB_DATA2 = 0xC2 # firmware 2.x
    TYPE_DTB_DATA  = None  # auto
    

    def tdoc(self, composite, ctype):
        """ helper for creating a readable doc string """
        if composite==RPC.SIMPLE and ctype=='v':return "void"
        elif composite==RPC.SIMPLE and ctype=="b": return "bool"
        elif composite==RPC.SIMPLE: return "int"
        elif composite==RPC.REFERENCE and ctype=="I": return "*int"
        elif composite==RPC.REFERENCE and ctype=="C": return "*int"
        elif composite==RPC.VECTORR and ctype=="S": return "*[]"
        elif composite==RPC.VECTORR and ctype=="C": return "*[]"
        elif composite==RPC.STRING and ctype=="c": return "string"
        elif composite==RPC.STRINGR and ctype=="c": return "*string"
        elif composite==RPC.HWVECTORR and ctype=="S": return "*[]"
        else: return "???"




    def __init__(self, name, rpcid, arglist, dtb = None ):
        self.name=name
        self.id = rpcid
        self.arglist = arglist
        self.dtb = dtb
        self.args = None

        # digest the argument list, see rpcgen/cpp_parser.cpp and rpc_calls.cpp
        # the first letter is the return type (always SIMPLE)

        self.returnType = arglist[0]  # may be v(oid)
        # the following entries are the argument types (simple or "composite")
        # create a list of (composite, type) pairs parallel to the arguments
        doc = "(%5s) %s (" % (self.tdoc(-1,self.returnType), name)
        self.argtypes=[]
        composite = RPC.SIMPLE  # if not specified
        if len( arglist) > 1:
            for c in arglist[1:]:
                if c in RPC.TYPES:
                    self.argtypes.append( (composite, c) )
                    doc += self.tdoc(composite, c)+","
                    composite = RPC.SIMPLE
                elif c in ('0','1','2','3','4','5'):
                    composite = int(c)
                else:
                    print "don't understand argument list ",arglist,
                    print "   for rpc ",name
                    sys.exit(1)
                    
        if doc[-1]==",":
            self.doc = doc[:-1]+")"
        else:
            self.doc=doc+")"
        self.nargs = len( self.argtypes ) # may be 0
        #print self.id, self.doc



    def read(self, n, timeout=100):
        """ read n bytes """
        if n==0:
            return ""
        
        nread, buf = self.dtb.usb.read_data(n)

        if self.DEBUG:
            print "* usb.read_data(%d) got %d/%d"%(n,nread,len(buf))
        ntry=0
        tstop=time.time()+timeout
        while len(buf) < n and time.time()<tstop:
            ntry+=1
            if ntry<100:
                time.sleep(0.01)
            else:
                time.sleep(0.1)
            nread, chunk =self.dtb.usb.read_data(n-len(buf))
            if nread>0:
                if self.DEBUG:
                    print "+[%d] read_data(%d) got %d/%d"%(ntry,n-len(buf),nread,len(chunk))
                buf += chunk

        if len(buf)<n:
            print "RPC.read (%s,%d) : timeout, "%(self.name,self.id),
            print len(buf),"/",n," bytes read"

        return buf
        



    def hexdump(self, buf, comment=None):
        if comment is not None:
            print comment,
        for b in buf:
            print "0x%02X "%ord(b),
        print

        
    def read_message(self):
        """ ~ rpcMessage.Receive """
        header = self.read(4)  # always 32 bits
        if len(header)<4:
            print "Warning! RPC.read_message only got ",len(header)
            return ""
        m_type = header[0]
        cmd = header[1:3]
        if not ( ord(m_type) & 0xFE) == RPC.TYPE_DTB: 
            print "Warning ! Unexpected message type  0x%02X"%(ord(m_type))
            self.hexdump( header , "received header ")
            print "call ",self.name
        size = struct.unpack('B', header[3])[0]
        #print "read_message  size=",size
        data = self.read( size )
        if not len(data) == size:
            print "Warning ! header data size=",len(data)," / ",size
        if RPC.DEBUG: print "reply:",; self.hexdump( header+data )
        return data
        


    def read_data(self):
        """ ~rpc_Receive, no error checking yet """
        header = self.read(4)
        if RPC.DEBUG: print "read_data header=",;self.hexdump(header)
        
        if len(header)<4:
            print "error reading data header"
            return None
            
        m_type = header[0]
        if ord(m_type) == RPC.TYPE_DTB_DATA1:
            size = struct.unpack('H', header[2:4])[0]
        else:
            size = struct.unpack('L', header[1:4]+chr(0))[0]
        
        # determine firmware 1.x vs 2.x
        if RPC.TYPE_DTB_DATA is None:
            RPC.TYPE_DTB_DATA = ord(m_type)

        if RPC.DEBUG: print "read data , size=",size
        data = self.read( size )
        return data
        


    def __call__(self, *args):

        if not len( args ) == self.nargs:
            print "bad argument list in call of ",self.name, self.id
            print "expected ",self.nargs," arguments,   got ",len(args)
            return

        if self.id is None:
            self.id = self.dtb.GetRpcCallId( self.name + "$" + self.arglist )

            
        if self.id <0 :
            print "bad rpc call: ",self.name+ "$" + self.arglist, self.id
            return
            
        self.args=args
       
            
        self.put = []
        self.getVect = [] # vector types need an extra receive
        
        size,fmt = RPC.TYPES[ self.returnType ]
        self.getR = [ (self.returnType, None) ]  #  return value + simple values returned "by reference"
        sizeR = size # total expected size
        
        parbuf=""
        put =  ""
        for i in range( self.nargs ):
            comp, ctype= self.argtypes[i]
            size, fmt = RPC.TYPES[ctype]

            if RPC.DEBUG : print "DEBUG rpc arg %d)"%i, comp, ctype, args[i],type(args[i])
            
            if comp == -1: # simple
                put += struct.pack( fmt, args[i] )

            elif comp == 0: # reference
                put += struct.pack( RPC.TYPES[ctype][1], args[i].value )
                self.getR.append( ( ctype,  args[i] ) )
                sizeR += size

            elif comp == 1: # vector
                for x in args[i]:
                    parbuf += struct.pack( fmt, x )
                 
            elif comp == 2: # vectorR
                self.getVect.append( ( RPC.VECTORR, ctype, args[i]) )
                
            elif comp == 3: # string
                if ctype=="c" and type(args[i])==str:
                    parbuf += args[i]
                else:
                    print "I am confused by ",comp,ctype,args
                    sys.exit(1)
                    
            elif comp == 4: # stringR?, can ctype be different from "c"?
                self.getVect.append( ( RPC.STRINGR, ctype, args[i] ) )
                
            elif comp == 5: # HWvectorR
                self.getVect.append( ( RPC.HWVECTORR, ctype, args[i]) )

        size = len( put )
        buf = UCHAR(0xC0) + USHORT( self.id ) + UCHAR( size ) + put
        stat = self.dtb.usb.write_data( buf )
        if RPC.DEBUG:  print "DEBUG %20s"%self.name,; print "stat=",stat; self.hexdump( buf , "sent :")


        # rpc_send data
        size = len( parbuf )
        if size>0:
            if RPC.TYPE_DTB_DATA == RPC.TYPE_DTB_DATA1:
                # bytes [TYPE, CH, SIZE, SIZE, DATA, .... ]  firmware 1.x
                buf =  UCHAR(RPC.TYPE_DTB_DATA)  + UCHAR( 0 ) + USHORT( size )
            else:
                # bytes [TYPE, SIZE, SIZE, SIZE, DATA, .... ] firmware 2.x
                buf = UCHAR(RPC.TYPE_DTB_DATA)  + ULONG( size )[:3]
            buf += parbuf
            stat = self.dtb.usb.write_data( buf )

        
        
        # do we expect a reply ?
        if sizeR==0 and len(self.getVect)==0:
            return

        self.dtb.usb.flush()

        # get return data ....
        buf = self.read_message()  # = msg.receive
        
        if not ( len(buf) == sizeR ):
            print "message data size mismatch, expected %d, got %d"%(sizeR, len(buf))
             
        # .. and extract return value and simple reference arguments
        idx = 0
        returnValue = False
        for ctype, ref in self.getR:
            size, fmt = RPC.TYPES[ctype]
            if size>0:
                try:
                    value = struct.unpack( fmt, buf[idx:idx+size] )[0]
                except:
                    print "struct error  fmt=",fmt,"  buffer=",buf[idx:idx+size]
                    value = 0
                    
                # make it a bool if that's what it's supposed to be
                if ctype == "b":
                    value = (value > 0)
                
                if ref is None:
                    returnValue = value
                else:
                    ref.value = value
            else:
                assert ref is None
            idx+=size
                

        if RPC.DEBUG:
            print "rpc.__call__  return value = ",returnValue



        # now get vector type arguments (VectorR, HWVectorR, StringR)
        # with additional transactions
        for composite, ctype, argument in self.getVect:

            if composite == RPC.STRINGR:

                time.sleep(0.02)
                result = self.read_data() # rpcReceive
                try:
                    argument.value = result
                except AttributeError:
                    print "argument not mutable, unable to pass string"

            elif composite in ( RPC.VECTORR, RPC.HWVECTORR) :

                try:
                    del argument[:]
                except TypeError:
                    print "argument must be a list "

                size, fmt = RPC.TYPES[ ctype ]
                buf = self.read_data() # rpcReceive
                n = len(buf)/size
                pos =0
                for k in range( n ):
                    value = struct.unpack( fmt, buf[pos:pos+size] )[0]
                    argument.append( value )
                    pos += size
                    
                    
                   
                
        return returnValue



    def getarg(self, argpos=0):
        """ return the cached value of the argument @ position argpos """
        if self.args:
            return self.args[ argpos ]
        else:
            print "argument undefined, never called ",self.name
            return None
            
            
########################################################################
# end of class RPC
########################################################################











########################################################################
class DTB(object):
    """ Digital Testboard access """
########################################################################

    
    TRIGGER_FIXED = 1
    TRIGGER_ROC = 2

    SYNC = 0x10
    RES = 0x08
    CAL = 0x04
    TRG = 0x02
    TOK = 0x01
    CAL_TRG_TOK = 0x07

    STRETCH_AFTER_CAL = 2
    #pixel_dtb.h
    SIG_CLK = 0
    SIG_CTR = 1
    SIG_SDA = 2
    SIG_TIN = 3

    # --- pulse pattern generator --------------------------------------
    PG_TOK  =   0x0100
    PG_TRG  =   0x0200
    PG_CAL  =   0x0400
    PG_RESR =   0x0800
    PG_REST =   0x1000
    PG_SYNC =   0x2000
    PG_NOP  =   0x0000

    # analog signal probes 
    PROBEA_TIN    = 0
    PROBEA_SDATA1 = 1
    PROBEA_SDATA2 = 2
    PROBEA_CTR    = 3
    PROBEA_CLK    = 4
    PROBEA_SDA    = 5
    PROBEA_TOUT   = 6
    PROBEA_OFF    = 7

    # digital signal probes e.g. SignalProbeD1(DTB.PROBE_PGSYNC)
    PROBE_OFF     = 0
    PROBE_CLK     = 1
    PROBE_SDA     = 2
    PROBE_SDA_SEND= 3
    PROBE_PGTOK   = 4
    PROBE_PGTRG   = 5
    PROBE_PGCAL   = 6
    PROBE_PGRESR  = 7
    PROBE_PGREST  = 8
    PROBE_PGSYNC  = 9
    PROBE_CTR     =10
    PROBE_TIN     =11
    PROBE_TOUT    =12
    PROBE_CLK_PRESEN = 13
    PROBE_CLK_GOOD   = 14
    PROBE_DAQ0_WR    =  15
    PROBE_CRC     =16
        #define PROBE_ADC_RUNNING 19
        #define PROBE_ADC_RUN 20
        #define PROBE_ADC_PGATE 21
        #define PROBE_ADC_START 22
        #define PROBE_ADC_SGATE 23
        #define PROBE_ADC_S 24
        
    BUFSIZE   = 8192  #  dtb DAQ buffer size (number of 16 bit words )
                      #  start with a small value compatible with fw1.x
    BLOCKSIZE = 8192*4  # number of 2-byte words transferred in one Daq_Read RPC
    #BLOCKSIZE = 512
      # number of 2-byte words transferred in one Daq_Read RPC

    def __init__(self, name="*", module=None, verbose=False, 
        rpcgen="rpcgen.log"):
            
        #verbose = True
        t0=time.time()
        self.serial = None
        if not self.open(name):
            sys.exit(1)
        self.verbose = verbose
        self.module = module
        self.rpcgen = rpcgen


        self.delayAdjust = 3
        self.deserAdjust = 4
        self.tct_wbc = 5
        self.sdaAdjust=15
        self.tinAdjust=5

        # some old style parameters for the "adc" command, may go away
        self.trc =  20    # 25
        self.tct = 101+5  # WBC+tct_wbc
        self.ttk =  32    # 16

        # always do this first, need to now fw1.x vs 2.x
        time.sleep(0.1)
        f0 = RPC( "GetRpcVersion", 0, "S", self)
        self.fwversion = f0()
        if self.fwversion >= 512:
            RPC.TYPE_DTB_DATA = RPC.TYPE_DTB_DATA2
            DTB.BUFSIZE = 50000000
        else:
            RPC.TYPE_DTB_DATA = RPC.TYPE_DTB_DATA1
            DTB.BUFSIZE = 8192
        print "DTB.BUFSIZE = ", DTB.BUFSIZE
            
        
        if rpcgen is None or rpcgen=="auto":
            # get the list of rpc calls from the DTB
            # let's hope that the first five are always the same....
            print "start bootsstrap",time.time()-t0
           
            # get the number of calls
            f3 = RPC( "GetRpcCallCount", 3, "i", self )
            nRPC = f3()
            if nRPC is None: 
                nRPC = f3() # just try again, don't know why it fails
            if verbose:
                print "retrieving RPC list from DTB "
                print "RPC count  = ",nRPC
            
            # get the call names (and arguments) 
            rpcnamelist = []
            f4=RPC( "GetRpcCallName", 4, "bi4c", self )
            name = StringR()
            for n in range(nRPC):
                print n
                success = f4(n, name)
                if success:
                    rpcnamelist.append( str( name ) )
                else:
                    print "unable to get rpc id ",n
                    print "start bootsstrap",time.clock()-t0
            print "end bootsstrap",time.time()-t0

        else:
            # get the rpc list from "rpcgen.log" if it exists
            filename = self.rpcgen
            try:
                print "reading RPC list",filename
                rpcnamelist = \
                  [ l.strip() for l in open(filename).readlines() ]
                print "RPC count  = ",len(rpcnamelist)
            except IOError:
                print "Unable to open", filename
                print "try running 'python DTB.py -rpcgen auto'"
                sys.exit(1)
            

        # create the RPC calls from the list
        self.rpclist=[] # keep a list, e.g. for the rpcinfo call
        for s in rpcnamelist: 
            cmd, arglist = s.strip().split("$")
            if cmd == "GetRpcVersion":
                cmdid=0
            elif cmd == "GetRpcCallId":
                cmdid=1
            else:
                cmdid=None # determine when needed

            # avoid overloading
            if not hasattr(self,cmd):
                name = cmd
            else:
                i=1
                while hasattr(self, cmd+"%d"%i):
                    i+=1
                name = cmd + "%d"%i

            # create a member function for each cmd string
            f=RPC( cmd, cmdid, arglist, self )

            # attach it to the DTB
            setattr( self, name, f )
            # and keep a list of functions
            self.rpclist.append( (name, f)  )

            # dummy code, just to catch mysterious errors
            #if cmdid==0:
            #    f()
        
        #print "temporarily dump rpcinfo"        
        #self.rpcinfo()
        
        # go configure 
        self.initialize( verbose=verbose )
########################################################################




########################################################################
    def open(self,name="*"):

        # initialize usb
        self.usb = USBInterface()

        if True:
            # try to list ftdi devices 0x6014
            ret, devices = self.usb.find_all( 0x0403, 0x6014 )

            if ret < 0:
                print( 'find_all failed: %d (%s)' % 
                       ( ret, self.usb.get_error_string(  ) ) )
                return
            
            if  ret==0 :
                print( 'No DTB found\n !' );
                return False;


            for i,dev in enumerate(devices):
                ret, manufacturer, description, serial = self.usb.get_strings( dev )
                if ret < 0:
                    print( 'ftdi_usb_get_strings failed: %d (%s)' % 
                           ( ret, self.usb.get_error_string() ) )
                    os._exit( 1 )

                if serial == name or ( name=='*' and len(devices)==1) :
                    print ( '-->  %2d    %s '%(i, serial) )
                    self.serial = serial
                else:
                    print ( '    %2d    %s '%(i, serial) )
                    
        # open usb
        ret = self.usb.open( 0x0403, 0x6014 )
        if ret < 0:
            print( 'unable to open ftdi device: %d (%s)' % 
                   ( ret, self.usb.get_error_string( ) ) )
            
                    
            return False


        return True
########################################################################









########################################################################
    def close(self):

        # close usb
        ret = self.usb.close(  )
        if ret < 0:
            print 'unable to close ftdi device: %d (%s)' \
                            % ( ret, self.usb.get_error_string(  ) ) 
            os._exit( 1 )
    
        print ('device closed')    
########################################################################



########################################################################
#    def uDelay(self, microSeconds):
#        time.sleep( microSeconds*1e-6 )
    def sleep(self, seconds):
        time.sleep(seconds)
########################################################################



########################################################################
    def rpcinfo(self):
        print "-"*80
        print "RPC info"
        print "-"*80
       
        for name, rpc in self.rpclist:
            if rpc.id is None:
                rpc.id = self.GetRpcCallId( rpc.name + "$" + rpc.arglist )      
            try:
                print "%2d"%rpc.id, rpc.doc.replace( rpc.name, name)
            except:
                print "error ",name
            #break
        print "-"*80
            
        boardId = self.GetBoardId()
        hw = StringR()
        self.GetHWVersion(hw)
        fwVersion = self.GetFWVersion()
        swVersion = self.GetSWVersion()
        rpcVersion = self.GetRpcVersion()
        print "board id   = ",boardId
        print "HW version =",hw
        print "FW version = %d.%02d"%(fwVersion/256, fwVersion%256)
        print "SW version = %d.%02d"%(swVersion/256, swVersion%256)
        print "RPCversion = %d.%02d"%(rpcVersion/256, rpcVersion%256)
        ts = StringR()
        self.GetRpcTimestamp( ts )
        print "RPC timestamp ",ts
        print "-"*80          
########################################################################



########################################################################
    def rpcdump(self):
        swVersion = self.GetSWVersion()
        filename="rpcgen-%02d%02d.log"%(swVersion/256, swVersion%256)
        try:
            f = open(filename, 'w')
        except IOError:
            print "DTB.rpcdump: unable to open file ",filename
            return
        for name, rpc in self.rpclist:
            f.write(rpc.name+"$"+rpc.arglist+"\n")
        f.close()
        print "created ",filename
        print "copy this file to rpcgen.log to make it the default"
########################################################################



        
########################################################################
    def setTiming(self,delay=None, deser=None, tct_wbc=None, sdaAdjust=None, tinAdjust=None):
        if not delay is None:
            self.delayAdjust = delay
        if not deser is None:
            self.deserAdjust = deser
        print "Timing values set : %d %d"%(self.delayAdjust, self.deserAdjust)
        self.Daq_Select_Deser160( self.deserAdjust )
        
        if not sdaAdjust is None:
            self.sdaAdjust = sdaAdjust
        if not tinAdjust is None:
            self.tinAdjust = tinAdjust
            
        self.Sig_SetDelay(DTB.SIG_CLK,  self.delayAdjust, 0 )
        self.Sig_SetDelay(DTB.SIG_SDA,  self.delayAdjust+self.sdaAdjust, 0 )
        self.Sig_SetDelay(DTB.SIG_CTR,  self.delayAdjust, 0 )
        self.Sig_SetDelay(DTB.SIG_TIN,  self.delayAdjust+self.tinAdjust, 0 )

        if tct_wbc:
            self.tct = self.tct - self.tct_wbc + tct_wbc
            self.tct_wbc = tct_wbc
########################################################################





########################################################################
    def deser160(self):
        """ adjust timing for a SingleROC assembly """
        # ported from pixel_dtb.cpp
        self.daq_Open( DTB.BUFSIZE )
        self.Pg_SetCmd(0, DTB.PG_TOK)
        data = []
        goodvalues=[]

        print("      0     1     2     3     4     5     6     7")
        for y in range(20):
            print "%2d:"% y,
            for x in range(8):
                self.Daq_Select_Deser160(x)
                self.Sig_SetDelay(DTB.SIG_CLK,  y, 0)
                self.Sig_SetDelay(DTB.SIG_SDA,  y+15,0)
                self.Sig_SetDelay(DTB.SIG_CTR,  y,0)
                self.Sig_SetDelay(DTB.SIG_TIN,  y+5,0)
                self.uDelay(10)

                self.daq_Start()
                self.Pg_Single()
                self.uDelay(10)
                self.daq_Stop()
                #self.daq_Read(data, 100)
                overflow = self.daq_read( data )

                if len(data)>0:
                    h = data[0] & 0xffc
                    if h == 0x7f8:
                        print "<%03X>"% int(data[0] & 0xffc),
                        goodvalues.append( (y,x) )
                    else:
                        print " %03X "% int(data[0] & 0xffc),
                else:
                    print "  ... ",
            print

        self.daq_Close();

        print "Old values: %d %d\n"%(self.delayAdjust, self.deserAdjust)
        if len(goodvalues) == 0:
            print "No value found where header could be read back ",
            print "- no adjustments made.\n"
            return True

        print("Good values are:")
        for x,y in goodvalues:
            print("%d %d"% (x,y))

        select = int( len(goodvalues)/2 )
        self.setTiming( *goodvalues[select])

        return True
########################################################################

    
        

########################################################################
    def getIA(self):
        """ returns the analog current in A """
        return self._GetIA()/10000.0

    def getID(self):
        """ returns the digital current in A """
        return self._GetID()/10000.0

    def getVD(self):
        return self._GetVD()/1000.

    def getVA(self):
        return self._GetVA()/1000.

    def setVD(self, v): # in V
        if 0. < v < 3.:
            self._SetVD( int(v*1000) )
        else:
            print "illegal value VD ",v

    def setVA(self, v): # in V
        if 0. < v < 2.5:
            self._SetVA( int(v*1000) )
        else:
            print "illegal value VA ",v


    def daq_read(self, buf):
        """ get all available data from the DTB daq buffer """
        del buf[:] 
        available = IntR()
        channel = 0
        while True:
            data = []
            overflow = self.Daq_Read1( data, DTB.BLOCKSIZE, available, channel)
            ##print "DTB.daq_read : read ",len(data),"  available ",available.value," ovflw=",overflow
            buf +=data
            if available.value==0: # or overflow>0
                break
        return overflow



            
    def daq_Read(self, data, blocksize=BLOCKSIZE, availsize=None, channel=0):
        # Daq_Read is overloaded in the firmware, it comes with
        # and without the availsize argument, which is a reference
        # and must be and IntR object
        if availsize is None:
            self.Daq_Read(data, blocksize, channel)
        else:
            self.Daq_Read1(data, blocksize, availsize, channel)

                
            #print "daq_Read dump (hw)vector:"
            #for b in data:
            #    print "{0:016b}".format( b ),
            #print
            
        
    # some versions with default arguments
    def daq_Open(self, bufsize = None, channel=0):
        if bufsize is None:
            bufsize = DTB.BUFSIZE
        self.daqBufsize = bufsize # remember this value
        return self.Daq_Open(bufsize, channel)
        
    def daq_Close(self, channel=0):    self.Daq_Close(channel)
    def daq_Start(self,channel=0):     self.Daq_Start(channel)
    def daq_Stop(self, channel=0):     self.Daq_Stop(channel)
    def daq_GetSize(self, channel=0): return self.Daq_GetSize(channel)
       
#######################################################################





########################################################################
    def setDAC(self, DAC, value):
        """ caching wrapper of the RPC roc_SetDAC """
        self.roc_SetDAC( DAC, value )
        # keep track of DAC settings
        rocId = self.roc_I2cAddr.getarg()
        self.module.roc[ rocId ].dacs[DAC]=value 
        self.cDelay( 5000 )
########################################################################


########################################################################
    def readEvent(self, event=None):
        if event is None:
            event=Event()
        data =  []
        if self.module.isSingleROC():
            overflow = self.daq_read(data)
            if len(data)==0:
                print "readEvent: no data "
                return event
            if len(data)>0:
                event.set_ROC(roc=0, header=data[0], data=data[1:])
            else:
                event.set_ROC(roc=0, header=data[0], data=[])
        elif True:#TBM08/deser400, see cmd.cpp
            #self.daq_Read(data, DTB.BLOCKSIZE, channel=0)
            overflow = self.daq_read(data)
            print "Hello World ",len(data)
            roc=None
            rocdata=[]
            tbm=None
            for b in data:
                print b
                q = (b>>4) & 0xf # "qualifier"
                d = b & 0xf
                if q==1: h=d 
                elif 1<q<6: h = (h<<4) + d
                elif q==6: 
                    rocdata.append( (h<<4) + d )
                # blabla
        # add isTBM08, TBM09, 2TBM09
        return event
            
########################################################################



########################################################################
    def readEvents(self):
        data =  []
        events = []
        
        if self.module.isSingleROC():
            available = IntR()
            overflow = self.daq_read( data )
            if len(data)==0:
                print "readEvents: no data "
                return []
            #if overflow >0 :
            #    print "DTB.readEvents: warning! Overflow ", overflow,len(data),self.daqBufsize
                
            # find ROC headers
            hi=[i for i in range(len(data)) if (data[i]& 0xff8) == 0x7f8]
            if len(hi)==0:
                print "no ROC headers"
                return []
            # split at header positions
            for start,end in zip( hi, hi[1:]+[len(data)]):
                event = Event()
                event.set_ROC(roc=0, header=data[start], data=data[start+1:end])
                events.append(event)

        elif False:#TBM08/deser400, see cmd.cpp
            roc=None
            rocdata=[]
            tbm=None
            for b in data:
                q = (b>>4) & 0xf # "qualifier"
                d = b & 0xf
                if q==1: h=d 
                elif 1<q<6: h = (h<<4) + d
                elif q==6: 
                    rocdata.append( (h<<4) + d )
                # blabla
        # add isTBM08, TBM09, 2TBM09
        return events
            
########################################################################





########################################################################
    def rocReset(self):
        """ send a reset,  !!! modifies the sequence inside the DTB !!! """
        self.pgset( (DTB.PG_REST+60,) )
        self.Pg_Single()
########################################################################




########################################################################
    def single(self,  seq =  RES+CAL+TRG+TOK):
        """ run a single sequnce,  !!! modifies the sequence inside the DTB !!! """
        cmdlist = []
        cmdlist.append(DTB.PG_SYNC + 10)
        if (seq & DTB.RES) > 0: cmdlist.append( DTB.PG_RESR + self.trc )
        if (seq & DTB.CAL) > 0: cmdlist.append( DTB.PG_CAL  + self.tct )
        if (seq & DTB.TRG) > 0: cmdlist.append( DTB.PG_TRG  + self.ttk )
        if (seq & DTB.TOK) > 0: cmdlist.append( DTB.PG_TOK  )
        self.pgset( cmdlist )
        self.Pg_Single()
        return
########################################################################
        


        
########################################################################
    def pgset(self, cmds=[], verbose=False):
        """ set up the pattern generator from a list of commands """
        self.Pg_Stop()
        sequence_length = 0
        ntrig, ntok = 0,0
        for n,c in enumerate(cmds):
            self.Pg_SetCmd( n, c )
            sequence_length += (c & 0xFF) + 1
            if c & self.PG_TOK >0:
                ntok +=1
            if c& self.PG_TRG>0:
                ntrig+=1
        self.Pg_SetCmd( len(cmds), 0)
        if verbose:
            print "sequence has ",ntrig," triggers  and ",ntok, "tokens  in ",
            print sequence_length*0.025," us"
        return sequence_length
########################################################################



        
########################################################################
    def adc(self, seq =  RES+TRG+TOK, ntrig=1, verbose=False, udelay=10, loopena=0, loopparam=4000, loopdelay=10381):
        """ emulate the old 'adc' but allowing other sequences than 15 
        the old variables trc, tct and ttk must be defined manually
        """

        if self.module.isSingleROC():
            self.Daq_Select_Deser160( self.deserAdjust ) # no idea why we need this

        cmdlist = []
        #to send sync signal (following the SignalProbeDx command)
        cmdlist.append(DTB.PG_SYNC + 10)
        if (seq & DTB.RES) > 0: cmdlist.append( DTB.PG_RESR + self.trc )
        # if (seq & DTB.SYNC) > 0:        
        #     cmdlist.append(DTB.PG_SYNC + 10)
        # else:
        #     cmdlist.append(10)
        #if (seq & DTB.CAL) > 0: cmdlist.append( DTB.PG_CAL  + 200  )
        if (seq & DTB.CAL) > 0: cmdlist.append( DTB.PG_CAL  + self.tct  )
        if (seq & DTB.TRG) > 0: cmdlist.append( DTB.PG_TRG  + self.ttk )
        if (seq & DTB.TOK) > 0: cmdlist.append( DTB.PG_TOK )
        self.pgset( cmdlist )
        
        self.daq_Close()
        self.daq_Open()
        self.daq_Start()
        self.usb.flush()
        
        #Better controlled trigger rate:
        if loopena == 1:
            #parameter in cc give seq length
            self.Pg_Loop(loopparam) #4000 -> 10 kHz
            #raw_input("ready to stop")
            for i in xrange(1000):
                self.uDelay(loopdelay) #1000*10381->100k
            self.Pg_Stop()
            self.usb.flush()
        
        else:
            for n in range(ntrig):
                self.Pg_Single()
                self.uDelay(udelay) # give enough time for readout            
                self.usb.flush()
        self.daq_Stop()
        
        if ntrig==1 and loopena == 0:
            event = self.readEvent()
            self.daq_Close()
            return event
        else:
            events = self.readEvents()
            self.daq_Close()
            return events
            
########################################################################

########################################################################
    def adc2(self, ntrig=1, verbose=False, udelay=10):
        """ emulate the old 'adc' but allowing other sequences than 15 
        the old variables trc, tct and ttk must be defined manually
        """

        if self.module.isSingleROC():
            self.Daq_Select_Deser160( self.deserAdjust ) # no idea why we need this

        cmdlist = []
        #to send sync signal (following the SignalProbeDx command)
        #cmdlist.append(DTB.PG_SYNC + 10)
        cmdlist.append( DTB.PG_RESR + self.trc )
        cmdlist.append( DTB.PG_CAL  + 200  )
        cmdlist.append( DTB.PG_SYNC +10 )
        cmdlist.append( DTB.PG_CAL  + 200  )
        cmdlist.append( DTB.PG_CAL  + self.tct  )
        cmdlist.append( DTB.PG_TRG  + self.ttk )
        cmdlist.append( DTB.PG_TOK )
        self.pgset( cmdlist )
        
        self.daq_Close()
        self.daq_Open()
        self.daq_Start()
        self.usb.flush()
        
        #Better controlled trigger rate:
        # self.Pg_Loop(4000) #10 kHz
        # for i in xrange(100):
        #     self.uDelay(1000) #->1000 triggers
        # self.Pg_Stop()
        
        for n in range(ntrig):
            self.Pg_Single()
            self.uDelay(udelay+random.randint(1,50)) # give enough time for readout            
            self.usb.flush()
        self.daq_Stop()
        
        if ntrig==1:
            event = self.readEvent()
            self.daq_Close()
            return event
        else:
            events = self.readEvents()
            self.daq_Close()
            return events
            
########################################################################

########################################################################
    def adc3(self, seq,ntrig=1, verbose=False, udelay=10):
        """ emulate the old 'adc' but allowing other sequences than 15 
        the old variables trc, tct and ttk must be defined manually
        """

        if self.module.isSingleROC():
            self.Daq_Select_Deser160( self.deserAdjust ) # no idea why we need this

        cmdlist = []
        #to send sync signal (following the SignalProbeDx command)
        #cmdlist.append(DTB.PG_SYNC + 10)
        if (seq & DTB.SYNC) > 0:
            cmdlist.append( DTB.PG_SYNC + 10 )
        if (seq & DTB.CAL) > 0:
            cmdlist.append( DTB.PG_CAL )
        cmdlist.append(self.tct)
        cmdlist.append( DTB.PG_TRG  + self.ttk )
        cmdlist.append( DTB.PG_TOK )
        self.pgset( cmdlist )
        
        self.daq_Close()
        self.daq_Open()
        self.daq_Start()
        self.usb.flush()
        
        #Better controlled trigger rate:
        # self.Pg_Loop(4000) #10 kHz
        # for i in xrange(100):
        #     self.uDelay(1000) #->1000 triggers
        # self.Pg_Stop()
        
        for n in range(ntrig):
            self.Pg_Single()
            self.uDelay(udelay+random.randint(1,50)) # give enough time for readout            
            self.usb.flush()
        self.daq_Stop()
        
        if ntrig==1:
            event = self.readEvent()
            self.daq_Close()
            return event
        else:
            events = self.readEvents()
            self.daq_Close()
            return events
            
########################################################################

########################################################################
    def daq(self, seq =  RES+TRG+TOK, runtime = 10, period=2000, verbose=False):
        """ like the adc command, but running in a loop mode for the numer 
        of seconds given by the runtime argument
        period is the period of the sequence in 25ns units 
        the maximum readout length is given by (period - (trc+tct+ttk)-3)/6
        """

        if self.module.isSingleROC():
            self.Daq_Select_Deser160( self.deserAdjust ) # no idea why we need this

        cmdlist = []
        if (seq & DTB.RES) > 0: cmdlist.append( DTB.PG_RESR + self.trc )
        if (seq & DTB.CAL) > 0: cmdlist.append( DTB.PG_CAL  + self.tct )
        if (seq & DTB.TRG) > 0: cmdlist.append( DTB.PG_TRG  + self.ttk )
        if (seq & DTB.TOK) > 0: cmdlist.append( DTB.PG_TOK )
        self.pgset( cmdlist )
    
        self.daq_Open()
        self.daq_Start()
        self.Pg_Loop( 2000 )
        time.sleep( runtime )
        self.daq_Stop()
        
        events = self.readEvents()
        self.daq_Close()
        return events
            
########################################################################



########################################################################
#  "higher level" functions
########################################################################
        
    def arm(self, col, row):
        self.roc_Col_Enable( col, True )
        self.roc_Pix_Trim( col, row, 15 )
        self.roc_Pix_Cal( col, row, False ) # True for Sensor

                      
    def mask(self, col=None, row=None):
        if col is None and row is None:
            self.roc_Chip_Mask()
        else:
            self.roc_Pix_Mask( col, row )


    def readback(self, seq=RES+TRG+TOK):
        """ ROC readback 
        what: must have been loaded as setDAC(255, what)
        0 - 3:Digital
          0   = LastData
          1   = Last Address
          2   = Last pixel col
          3   = last pixel row
        8 - 12:Analog
          8   = VD unreg
          9   = VA unreg
         10  = VA reg  
         11  = Vbg
         12  = Ianalog
        comment: 10/11 have twice the sensitivity that 8/9 have
        """
        
        value={}
        start={}
        events = self.adc( seq , ntrig=32)
        if len(events)<32:
            print "Error: readback only got ",len(events)," event(s)"
            return None
            
        for roc in events[0].get_ROCs():
            value[roc]=0
            start[roc]=0

        for e in events:
            for roc in e.get_ROCs():
                S,D = e.get_ROCheader(roc)
                if start[roc]==1:
                    value[roc] = (value[roc] << 1 ) + D
                if S==1:
                    start[roc] +=1
                    
              
        results =OrderedDict()
        for roc in sorted(value):
            roc_readback  = ( value[roc] & 0xF000 ) >> 12
            cmd_readback  = ( value[roc] & 0x0F00 ) >> 8
            data  = ( value[roc] & 0x00FF )
            results[roc]=(data, cmd_readback, roc_readback)
        return results
            
        
        
        
    def readLastDAC(self, roc=None):
        # self.setDAC(255, 0) must have been set at some point
        results = self.readback()
        if roc is None:
            return { rocid:results[rocid][0] for rocid in results }
        else:
            return results[roc][0]
 
        
    def readADC(self, what, roc=None):
        self.setDAC(255, what)
        results = self.readback()
        if results is None:
            return None
        if roc is None:
            return { rocid:results[rocid][0] for rocid in results }
        else:
            return results[roc][0]

########################################################################



########################################################################
    def singleRocOnePixelPhScan(self, rocid, col, row, ntrig=1, flag=0, dac=25, dacmin=0, dacmax=255):
        """ dacs scan via rpcs, returns a list of pairs(dac, ph) """
        self.Daq_Select_Deser160( self.deserAdjust )   
        self.daq_Open()
        self.daq_Start()
        self.LoopSingleRocOnePixelDacScan(rocid, col, row, ntrig, flag, dac, dacmin, dacmax)
        self.daq_Stop()
        t=self.daq_GetSize(0)
        chunk = self.readEvents()
        self.daq_Close()
        expected = 256*ntrig
        print len(chunk), expected,t
        xy = []
        for dac in range(dacmin, dacmax+1):
            n,ph=0,0
            offset=(dac-dacmin)*ntrig
            events = chunk[offset:offset+ntrig]
            for e in events:
                for roc, pcol, prow, pph in e.hits():
                    if prow==row and pcol==col:
                        ph += pph
                        n+=1
                    else:
                        print "unexpected hit found ",roc,pcol, prow
                        
            if n>0:
                xy.append( (dac, float(ph)/float(n)) )

        return xy




########################################################################
    def singleRocOnePixelScan(self, rocid, col, row, ntrig=10, flag=0, dac=25, dacmin=0, dacmax=255):
        """ dacs scan via rpcs, returns a list of tuples(dac, nhit, ph) """
        self.Daq_Select_Deser160( self.deserAdjust )   
        self.daq_Open()
        self.daq_Start()
        self.LoopSingleRocOnePixelDacScan(rocid, col, row, ntrig, flag, dac, dacmin, dacmax)
        self.daq_Stop()
        t=self.daq_GetSize(0)
        chunk = self.readEvents()
        self.daq_Close()
        expected = 256*ntrig
        print len(chunk), expected,t
        xy = []
        for dac in range(dacmin, dacmax+1):
            n,ph=0,0
            offset=(dac-dacmin)*ntrig
            events = chunk[offset:offset+ntrig]
            for e in events:
                for roc, pcol, prow, pph in e.hits():
                    if prow==row and pcol==col:
                        ph += pph
                        n+=1
                    else:
                        print "unexpected hit found ",roc,pcol, prow
                        
            if n>0:
                xy.append( (dac, n, float(ph)/float(n)) )
            else:
                xy.append( (dac, n, None) )

        return xy



        
        
########################################################################
# initialization / configuration
########################################################################
    
    def readDacParameterFile(self, path):
        print "reading ",path
        dacname2number={'vnpix': 23, 'iana': 2, 'vibias_dac': 20, 'globalthr': 12, 'adcpower': 19, 'vleak': 5, 'readback': 255, 'vcomp': 4, 'vbias_sf': 14, 'phoffset': 17, 'vsf': 3, 'vsh': 3, 'vwllpr': 7, 'vibiasop': 16, 'fbsh': 9, 'vrgpr': 6, 'rbreg': 255, 'vthrcomp': 12, 'vhlddel': 10, 'voffsetro': 17, 'vcomp_adc': 19, 'vibias_ph': 19, 'voffsetop': 15, 'vsumcol': 24, 'trimscale': 11, 'wbc': 254, 'vion': 18, 'holddel': 10, 'vtrim': 11, 'fbpre': 7, 'vwllsh': 9, 'vicolor': 22, 'caldel': 26, 'vleak_comp': 5, 'vana': 2, 'vdig': 1, 'vcal': 25, 'vrgsh': 8, 'ctrlreg': 253, 'ccr': 253, 'vibias_bus': 13, 'ibias_dac': 20, 'viref_adc': 20, 'vdd': 1, 'phscale': 20, 'vbias_op': 16, 'vibias_roc': 21}

        for l in open(path).readlines():
            fields = l.split()
            if len(fields)==3:
                dacid, dacname, dacvalue = l.split()
            elif len(fields)==2:
                dacname, dacvalue = l.split()
                dacid=0
            else:
                print "reading dacParameter file, skipping line ",l
                continue
                
            if dacname in dacname2number:
                dacid=dacname2number[dacname]
                self.setDAC( dacid, int(dacvalue) )
            if dacid>0:
                # psi46expert style
                self.setDAC(  int(dacid), int(dacvalue) )

    
    def readTrimParameterFile(self, path):
        for l in open(path).readlines():
            trimValue, dummy, col, row = l.split()
            self.roc_Pix_Trim( int(col), int(row), int(trimValue) )


    def configureROC(self, rocId=0, dir=None, verbose=False):
        self.roc_I2cAddr( rocId ) 
        print "configuring ROC",rocId,"dir=",dir
        if dir is None:
            self.setDAC(  1,   6)#       Vdig
            self.setDAC(  2, 113)#       Vana
            self.setDAC(  3,   0)#       Vsf
            self.setDAC(  4,  12)#      Vcomp
            self.setDAC(  7,  60)#     VwllPr 
            self.setDAC(  9,  60)#     VwllSh
            self.setDAC( 10, 255)#    VhldDel
            self.setDAC( 11,  29)#     Vtrim
            self.setDAC( 12,  20)#  VthrComp
            self.setDAC( 13,  20)# VIBias_Bus
            self.setDAC( 14,   6)#   Vbias_sf
            self.setDAC( 15,  40)#  VoffsetOp
            self.setDAC( 17, 130)#  VOffsetR0
            self.setDAC( 18, 120)#       VIon
            self.setDAC( 19, 100)#  Vcomp_ADC
            self.setDAC( 20,  80)#  VIref_ADC
            self.setDAC( 21, 150)# VIbias_roc
            self.setDAC( 22,  20)#   VIColOr
            self.setDAC( 25, 199)#       Vcal
            self.setDAC( 26,  64)#     CalDel
            self.setDAC(253,   0)#    CtrlReg
            self.setDAC(254, 101)#        WBC
            self.setDAC(255,   0)#   readback
        else:
            self.readDacParameterFile(os.path.join(dir, 
                "dacParameters_C%d.dat"%rocId) )

            #path = os.path.join( dir, "trimParameters_C%d.dat"%rocId )
            #self.readTrimParameterFile(path)
            
        #self.roc_ClrCal()
        #self.mask()


    
    def initialize(self, verbose=False, rocversion="digv2"):

        self.rocversion = rocversion
        self.rowinvert = ( rocversion in ["digv1","digtrig"])
        self.Init()
        self.Welcome()
        self.Pon()
        if verbose:
            boardId = self.GetBoardId()
            hw = StringR()
            self.GetHWVersion(hw)
            fwVersion = self.GetFWVersion()
            swVersion = self.GetSWVersion()
            print "board id   = ",boardId
            print "HW version =",hw
            print "FW version = %d.%02d"%(fwVersion/256, fwVersion%256)
            print "SW version = %d.%02d"%(swVersion/256, swVersion%256)
        
        self._SetIA( 10000 )
        self._SetID( 10000 )
        self.setVD( 2.500 )
        self.setVA( 1.600 )
        self.setTiming()
        time.sleep(1)
        
        if self.module is None:
            print "no ROC / Module specified"
        else:
            if self.module.isSingleROC():
                self.tbm_Enable(False)
                self.SetRocAddress( self.module.rocId )
                self.configureROC( self.module.rocId, dir=self.module.dir )
            else:
                # something must happen here to set the hub id
                # and to configure the tbm
                for rocId in self.module.rocIds():
                    self.configureROC( rocId, dir=self.module.dir )
                
                

        if verbose:
            print "VD = ",self.getVD(),"V"
            print "VA = ",self.getVA(),"V"
            print "IA = ",self.getIA(),"A"
            print "ID = ",self.getID(),"A"
            
            
    def enableRoc(self, column=None, columns=None, 
        row=None,  rows=None, trim=15):
        """ enable and trim the roc or parts of it """
        if column is None and columns is None:
            columns =  range(52)
        elif columns is None:
            columns = [column]
        
        if row is None and rows is None:
            rows = range(80)
        elif rows is None:
            rows = [row]
            
        for col in columns:
            self.roc_Col_Enable( col , True)
            for row in rows:
                self.roc_Pix_Trim(col, row, trim)





    def autoroc(self, iatarget = 0.024):
        """ setup iana and tct for a single ROC """
        # set iana roc
        print "starting roc configuration"
        ia = self.getIA()
        print "Ia = ",ia," A"
        if abs(ia-iatarget)>0.001:
            
            self.setDAC(2, 0)
            time.sleep(0.2)
            imin = (0, self.getIA())
            imin = (0, self.getIA())
            print imin
            self.setDAC(2,255)
            time.sleep(0.2)
            imax = (255, self.getIA())
            imax = (255, self.getIA())
            print imax

            while (imax[1]-imin[1])>0.001:
                dac = (imin[0]+imax[0] ) //2
                self.setDAC(2,dac)
                time.sleep(0.2)
                ia = self.getIA()
                ia = self.getIA()
                print dac,ia
                if ia>iatarget:
                    imax = (dac,ia)
                else:
                    imin = (dac,ia)
            print "set vana ",dac, "   ia=",ia
            
            
        print "setting vthrcomp"
        vcorg=self.module.roc[0].dacs[12]
        idigorg = self.getID()
 
        self.module
        time.sleep(0.5)
        self.getID()
        idig=[ (self.getID()+self.getID()+self.getID())/3.  ]
        vcset=10
        for vc in range(10,150,10):
            self.setDAC(12, vc)
            time.sleep(0.1)
            self.getID()
            idig.append( (self.getID()+self.getID()+self.getID())/3. )
            s=float(idig[-1]-idig[-2])/idig[0]
            #print vc,idig[-1],s
            if s<0.1:
                vcset = vc
            else:
                break
        
        if vcset>20:
            vcset -=20
        print "setting vcthrcomp=",vcset
        self.setDAC(12,vcset)
        


        print "setting tct"
        self.arm(20, 20)
        wbc = self.module.roc[0].dacs[254]
        print "wbc is ",wbc
        for tct in range(wbc, wbc+20):
            self.tct = tct
            e = self.adc(15)
            if len(e)>0:
                print "tct ",tct, e
                break
                
        #a =self.singleRocOnePixelScan(0, 20, 20, ntrig=10, flag=0, dac=25, dacmin=0, dacmax=255)



########################################################################
# end of class DTB
########################################################################





   
########################################################################
# container for ROC/Module readout data
########################################################################
class Event(object):
    def __init__(self):
        self.tbmHeader = None
        self.rocHeader = {}
        self.rocData = {}   # per ROC, list of tuples(col, row, ph)
        self.tbmTrailer = None
        self.valid = False
        
    def __len__(self):
        """ return the total number of hits """
        return sum([len(self.rocData[roc]) for roc in self.rocData])
        
    def hits(self):
        for roc in sorted(self.rocData):
            for col, row, ph in self.rocData[roc]:
                yield roc, col, row, ph
        
        
    def get_ROCs(self):
        return sorted(self.rocData)
        
    def set_ROC(self, roc=0, header=0, data=[]):
        self.rocHeader[roc] = self.decode_ROCheader( header )
        self.rocData[roc] = self.decode_ROCdata( data )

    def get_ROCheader(self, roc):
        return self.rocHeader[roc]
        
    def decode_ROCheader(self, header):
        if not (header & 0xff8) == 0x7f8:
            print "invalid header {0:012b}".format( header )
            self.valid=False
            return (-1, 0)
        else:
            S = (header & 2) >>1
            D =  header & 1
            self.valid=True
            return (S, D)

        
    def decode_ROCdata(self, data):
        """ decodes the (DESER160) data stream of psi46digv2 ROCs 
        returns a list of (col, row, pulse-height) tuples
        """
        hits = []
        size=len(data)
        b=0
        while b+1< size:
            w = ((data[b] & 0x0fff)  << 12) + (data[b+1] & 0x0fff)

            # extract the pulse-height, remove the dummy "0" in the middle
            ph = (w & 0x0f) + ((w>>1) & 0xf0)
            # and the addresses, shift out the pulse-height
            a = (w >>9)
            # rowinvert??
            c =  ( a>>12) & 7
            c= c*6 + ((a>> 9) & 7)
            r =      ((a>> 6) & 7)
            r= r*6 + ((a>> 3) & 7)
            r= r*6 + ( a      & 7)

            row=80-r/2
            col=2*c+(r&1)
            hits.append( (col, row, ph) )
            b+=2
            if (row>79) or  (col>51) or  (ph>255):
                valid = False
        return hits
       
    def is_valid(self):
        return self.valid
        
    def __str__(self):
        """ 
        """
        s=""
        # tbm
        # rocs
        for roc in sorted(self.rocData):
            S,D = self.rocHeader[roc]
            s+="[%2d(S%1d,D%1d) "%(roc,S,D)
            npx=0
            for col,row,ph in self.rocData[roc]:
                if (row==80):
                    s+=" !(%2d, %2d: %3d)*"%(col, row, ph)
                elif (row<0) or (row>80) or (col<0) or (col>51) or  (ph>255):
                    s+=" *(%2d, %2d: %3d)*"%(col, row, ph)
                else:
                    s+=" (%2d, %2d : %3d)"%(col, row, ph)
                npx+=1
                if npx>100:
                    s+= " + "+str(len(self.rocData[roc])-npx)+" more pixels"
                    break
            s+="] "
        return s
        
########################################################################





########################################################################
# containers for ROC/Module configuration
########################################################################

class ROC(object):
    """ hold configuration data of a ROC 
        the DTB class may or may not track changes
    """
    def __init__(self):
        self.dacs={}


class Module(object):
    """ module or single roc assembly connected to a DTB """
    def __init__(self):
        self.roc = OrderedDict()
    def rocIds(self): return self.roc.keys()
    def isSingleROC(self): return False

    
class SingleROC(Module):
    """ single roc assembly connected to a DTB """
    def __init__(self, rocId=0, dir=None, rocversion="psi46digv2"):
        self.rocId=rocId
        self.roc = OrderedDict( [(rocId, ROC())] )
        self.dir=dir
        self.rocversion=rocversion
    def isSingleROC(self): return True
        
class L2HDI(Module):
    """ HDI with tbm but no ROCs """
    def __init__(self, hubId=31, dir=None):
        super(L2HDI, self).__init__()
        self.hubId = hubId
        self.dir=dir

class L2Module(Module):
    """ work in progress """
    def __init__(self, hubId=31, dir=None):
        self.hubId = hubId
        self.dir=dir
        self.rocs = OrderedDict( [( i , ROC()) for i in range( 16 )] )
########################################################################


        


########################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-rpcgen", default="rpcgen.log",
                        help="'auto' or file containing the list of RPCs")
    parser.add_argument("-rpcinfo", action="store_true", default=False,
                        help="print the list of rpc calls")
    parser.add_argument("-d", help="directory with module or roc data")
    parser.add_argument("-singleROC", action="store_true")
    
    
    args = parser.parse_args()
    
    if args.singleROC:
        M = SingleROC(rocId=0, dir=args.d)
    else:
        M = None
    
    tb=DTB(name="*", module=M, verbose = True, rpcgen=args.rpcgen)
    tb.SetLed(1)
    
    if args.rpcinfo:
        tb.rpcinfo()
        
    if args.rpcgen=="auto":
        tb.rpcdump()
    
    tb.SetLed(0)
    
    
    

    if M is None:
        sys.exit(0)

    tb.roc_ClrCal()
    tb.arm(20, 20)
    

    wbc = M.roc[0].dacs[254]
    for tct in range(wbc, wbc+10):
        tb.tct = tct
        e = tb.adc(15)
        if len(e)>0:
            print "tct ",tct, e
            break
        

    print "the good old adc command ", tb.adc(15)
    e = tb.adc( 7 )
    print "and again                ", e
    print "dump it using the Event.hits() generator "
    for roc,col, row, ph in e.hits():
        print roc, col, row, ph
    
    print "multiple "
    for n,e in enumerate( tb.adc(15, ntrig=5) ):
        print n+1, e

    sys.exit()
    
    tb.setDAC(255,0) # allow last dac readback
    tb.setDAC( 2, 100)
    print "ia = ",tb.getIA()
    print "Ia(readback) = ",tb.readLastDAC(0)
        
    tb.setDAC( 2, 200)
    time.sleep(1)
    print "ia = ",tb.getIA()
    print "Ia(readback) = ",tb.readLastDAC(0)
    
    print "ADC ia       ",tb.readADC(12,0)
    print "ADC vd_unreg ",tb.readADC( 8,0)
    #print " ",tb.readADC( )
    tb.Poff()
    
    
    
    
    tb.close()
