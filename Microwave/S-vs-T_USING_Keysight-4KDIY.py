
import stlab
import datetime
import time
import numpy as np
from stlab.devices.Cryocon_44C import Cryocon_44C

dev = Cryocon_44C('TCPIP::192.168.1.4::5000::SOCKET')
device = stlab.adi(addr='TCPIP::192.168.1.230::INSTR',reset=True,verb=True)

numPoints = 1001
startFreq = 5200000000.0
stopFreq = 5400000000.0

tdelay = 30 #time between meas
tmeas = 300 #total time measuring

prefix = 'Test' #prefix for measurement folder name.  Can be anything or empty
idstring = 'Timed' #Additional info included in measurement folder name.  Can be anything or empty



device.write('INST:SEL "NA"')  #set mode to Network Analyzer
device.SinglePort() #changed this to from twoport to singleport
#        frec = self.query('FREQ:DATA?')
device.write("SENS:SWE:POIN " + str(numPoints))

device.write("SENS:FREQ:START " + str(startFreq))

device.write("SENS:FREQ:STOP " + str(stopFreq))

#device.write("SENS:DIF:BAND " + str(bandwidth)) #this crashes the fieldfox error -113
device.SetIFBW(100.)

tdelay = 30

t0 = time.time()
t = 0
myfile = stlab.newfile(prefix,idstring,autoindex=True)
while t < tmeas:
        tt = time.time()
        t=tt-t0
        data = device.MeasureScreen_pd()
        data['Temperature (K)'] = dev.GetTemperature('A')
        data['Time (s)'] = t

        stlab.saveframe(myfile, data, delim=',') #Save measured data to file.  Written as a block for spyview.
        time.sleep(tdelay)


myfile.close()
