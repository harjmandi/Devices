''' 
This program uses Keysight_B2901A for IV measurement (V bias) at zero gate.
 
'''



import stlab
import stlabutils
from stlab.devices.TritonWrapper import TritonWrapper
import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
from stlab.devices.Keysight_B2901A import Keysight_B2901A
import os
import sys



''' input ''' 
prefix = 'F17_IV_h12_VBias_5mV'


V_bias_max = 5e-3 # [uV] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[uV], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/100 #[uV]
average_I = 20 #number of current measurement per Voltage point
bias_time_sleep = 0.1 # sleep time between each current measurement


''' Initialize '''  
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
mytriton = TritonWrapper()

try:
    T = mytriton.GetTemperature(8)
except:
    T = -1

# Keysight setting
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeVoltage()
B2901A.write('SENS:CURR:PROT 0.01') #set the current compliance limit to 10mA
B2901A.SetOutputOn()

## Output setting
idstring = '_at{:.2f}mK'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'T (mK)', 'Time (s)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)


V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)

END = False

plt.rcParams["figure.figsize"] = [16,9] 



''' Start the measurement '''


## Ramping up the gate to the first point

last_time = time.time()


current_array = []
VBias_array = []

B2901A.RampVoltage(V_bias_list[0],tt=5., steps = 10)  #biasing    


## Sweeping the bias voltage
for count, V_bias in enumerate(V_bias_list): 

    for event in pygame.event.get():
      if event.type == QUIT:sys.exit()
      elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
        END = True

    if END:
      break
           
    B2901A.SetVoltage(V_bias)  #biasing at reverse Voltage 
    time.sleep(1)

    I = 0
    for i in range (average_I):
        I += B2901A.GetCurrent()
        time.sleep(bias_time_sleep)

    current_array = np.append(current_array,I/average_I)
    VBias_array = np.append(VBias_array,V_bias) 

    current_time = time.time()
    line = [V_bias, I, T, current_time - last_time]
    stlab.writeline(myfile, line)
    
    myfile.write('\n')

    plt.subplot(2, 1, 1)
    plt.title(prefix)
    plt.ylabel('current [$\mu$A]')
    plt.xlim(V_bias_min*1e3,V_bias_max*1e3)
    plt.plot(VBias_array*1e3,current_array*1e6, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9)


    if count > 0:
        plt.subplot(2, 1, 2)
        plt.plot(VBias_array[1:]*1e3,np.diff(VBias_array)/np.diff(current_array), '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9)

        plt.xlabel('bias Voltage [mV]')
        plt.ylabel('resistance [$\Omega$]')

        plt.xlim(V_bias_min*1e3,V_bias_max*1e3)

        plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
B2901A.RampVoltage(0,tt=20, steps = 5)  #biasing at reverse Voltage   
B2901A.close()
myfile.close()

