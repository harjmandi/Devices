
import stlab
import numpy as np

prefix = 'C26_UL-noGate_' #prefix for measurement folder name.  Can be anything or empty
caption = 'measurement with no amplification and no circulator/directional coupler POWER:-10 dBm'
path = 'D:\\measurement_data_4KDIY\\Hadi\\C26 2020-02-26 measurements/'


KEYSIGHT = stlab.adi(addr='TCPIP::192.168.1.230::INSTR',reset=False,verb=True)

numPoints = 1001
startFreq =2e9
stopFreq = 5e9
power = -10


KEYSIGHT.write('INST:SEL "NA"')  #set mode to Network Analyzer
KEYSIGHT.SinglePort() #changed this to from twoport to singleport
KEYSIGHT.write("SENS:SWE:POIN " + str(numPoints))
KEYSIGHT.write("SENS:FREQ:START " + str(startFreq))
KEYSIGHT.write("SENS:FREQ:STOP " + str(stopFreq))
KEYSIGHT.SetPower(power)

#device.write("SENS:DIF:BAND " + str(bandwidth)) #this crashes the fieldfox error -113
KEYSIGHT.SetIFBW(100.)


myfile = stlab.newfile(prefix,'_',autoindex=True, mypath= path)

data = KEYSIGHT.MeasureScreen_pd()

stlab.saveframe(myfile, data) #Save measured data to file.  Written as a block for spyview.
myfile.close()

stlab.autoplot(myfile,'Frequency (Hz)','S11dB (dB)',title=prefix,caption=caption)
stlab.autoplot(myfile,'Frequency (Hz)','S11Ph (rad)',title=prefix,caption=caption)

