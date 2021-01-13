"""
I did not manage to have it working yet. 
Use the examples in this page to solev the issues: 
https://stackoverflow.com/questions/26263835/programming-with-connected-hardware
"""




"""Module implementing basic Keithley digital multimeter

This module is the base class for Keithley DMMs 2000, 2100 and 6500
"""



import numpy as np
import time
import pyvisa
import visa
rm = pyvisa.highlevel.ResourceManager()



def numtostr(mystr):
    return '%20.15e' % mystr


# class TENMA:
#     def __init__(self, address_string = "ASRL8::INSTR"):
#         self.ps = rm.open_resource(address_string, baud_rate = 9600, data_bits = 8)
#         if self.ps is None:
#             raise PowerSupplyException('Unable to open resource GPIB0::12::INSTR')
#         self.write_termination = '\n'
#         self.read_termination = '\n'
#         self.send_end = True
#         self.StopBits = 1
#         self.ps.query("*IND?")

class TENMA:
    def __init__(self):
        pass
        # self.ps = rm.open_resource("ASRL8::INSTR")
        # # self.ps.write_termination = '\n'
        # # self.ps.read_termination = '\n'
        # # self.ps.send_end = True
        # # self.ps.query('*IND?\n')

    def getVoltage(self):
        return self.query('VOUT1?')
    def setVoltage(self,v):
        self.write('VOLT '+str(v))


    # def __init__(self,
    #              addr='COM8',
    #              ndacs=8,
    #              polarity=('BIP', 'BIP'),
    #              verb=True,
    #              timeout=2,
    #              reset=False):
    #     #Directly using pyserial interface and skipping pyvisa
    #     self.serialport = serial.Serial(
    #         addr,
    #         baudrate=9600,
    #         bytesize=serial.EIGHTBITS,
    #         parity=serial.PARITY_NONE,
    #         stopbits=serial.STOPBITS_ONE,
    #         timeout=timeout)
    #     if ndacs != 8 and ndacs != 16:
    #         print(
    #             'DAC WARNING, non-standard number of dacs.  Should be 8 or 16 but %d was given'
    #             % ndacs)
    #     self.ndacs = ndacs
    #     self.verb = verb
    #     self.SetPolarity(polarity)
    #     if reset:
    #         self.RampAllZero(tt=20.)
    #     return
    #     # self.lastmessage = ()
    #     # super().__init__()

    def WhoIsIt(self):
        self.query("*IND?")

    
    def SetVoltage(self, Vol):
        mystr = numtostr(Vol)
        mystr = 'VSET1:' + mystr
        self.write(mystr)


    def GetVoltage(self):  # (manual entry) Preset and make a DC voltage measurement with the specified range and resolution. The reading is sent to the output buffer.
        # range and res can be numbers or MAX, MIN, DEF
        # Lower resolution means more digits of precision (and slower measurement).  The number given is the voltage precision desired.  If value is too low, the query will timeout
        volt = self.query('VOUT1?')
        return float(volt)

    def GetCurrent(self):  # (manual entry) Preset and make a DC current measurement with the specified range and resolution. The reading is sent to the output buffer.
        # range and res can be numbers or MAX, MIN, DEF
        # Lower resolution means more digits of precision (and slower measurement).  The number given is the voltage precision desired.  If value is too low, the query will timeout
        num = self.query("IOUT1?")
        return float(num)

    def RampVoltage(self, mvoltage, tt=5., steps=100):  #To ramp voltage over 'tt' seconds from current DAC value.
        v0 = self.GetVoltage()
        if np.abs(mvoltage - v0) < 1e-2:
            self.SetVoltage(mvoltage)
            return
        voltages = np.linspace(v0, mvoltage, steps)
        twait = tt / steps
        for vv in voltages:
            self.SetVoltage(vv)
            time.sleep(twait)


    def TurnOn(self):
        self.write("OUT1")


    def TurnOff(self):
        self.write("OUT0")

    def Close(self):
        self.close()

