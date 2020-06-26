'''
This program uses Keysight_B2901A for IV measurement (V bias) at zero gate.

'''



import stlab
import stlabutils
import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
from stlab.devices.Keysight_B2901A import Keysight_B2901A
import os
import sys



''' input '''
prefix = 'F20_IV_e3-1to3_VBias_B2901'
path = 'D:/measurement_data_4KDIY/Hadi/F20 2020-05-11 measurements/'


V_bias_max = 1.5 # [V] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[V], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/50 #[V]
average_I = 5 #number of current measurement per Voltage point
bias_time_sleep = 0.1 # sleep time between each current measurement


''' Initialize '''
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
T = 5.9

# Keysight setting
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeVoltage()
B2901A.write('SENS:CURR:PROT 0.01') #set the current compliance limit to 10mA
B2901A.SetOutputOn()

## Output setting
idstring = '_at{:.2f}K'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'T (K)', 'Time (s)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)


V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)

END = False




''' Start the measurement '''


## Ramping up the gate to the first point

last_time = time.time()


current_array = []
VBias_array = []

B2901A.RampVoltage(V_bias_list[0],tt=5., steps = 10)  #biasing


## Sweeping the bias voltage
for count, V_bias in enumerate(V_bias_list):

    if END:
      break

    B2901A.SetVoltage(V_bias)  #biasing at reverse Voltage
    time.sleep(1)

    I = 0
    for i in range (average_I):
        for event in pygame.event.get():
          if event.type == QUIT:sys.exit()
          elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
            END = True

        if END:
          break


        I += B2901A.GetCurrent()
        time.sleep(bias_time_sleep)

    current_array = np.append(current_array,I/average_I)
    VBias_array = np.append(VBias_array,V_bias)
    R_array = np.diff(VBias_array)/np.diff(current_array)

    current_time = time.time()
    line = [V_bias, I, T, current_time - last_time]
    stlab.writeline(myfile, line)

    myfile.write('\n')

    plt.rcParams["figure.figsize"] = [16,9]

    plt.subplot(2, 1, 1)
    plt.title(prefix)
    plt.ylabel('current [$\mu$A]')
    plt.xlim(V_bias_min*1e3,V_bias_max*1e3)
    plt.plot(VBias_array*1e3,current_array*1e6, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9)


    if count > 0:
        plt.subplot(2, 1, 2)
        plt.plot(VBias_array[1:]*1e3,R_array, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9)

        plt.xlabel('bias Voltage [mV]')
        plt.ylabel('dV/dI [$\Omega$]')

        plt.xlim(V_bias_min*1e3,V_bias_max*1e3)
        plt.ylim(0, 3000)

    plt.pause(0.1)


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
B2901A.RampVoltage(0,tt=20, steps = 20)  #biasing at reverse Voltage
B2901A.close()
myfile.close()

