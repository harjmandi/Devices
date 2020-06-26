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
from stlab.devices.keysightB2961A import keysightB2961A as Keysight_B2961A

import os
import sys



''' input '''
prefix = 'F20_IV_e3-1to2-floating34_VBias_B2901'
path = 'D:/measurement_data_4KDIY/Hadi/F20 2020-05-11 measurements/'


V_bias_max = 2 # [V] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[V], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/50 #[V]
average_I = 5 #number of current measurement per Voltage point
bias_time_sleep = 0.1 # sleep time between each current measurement

# Vg_max = 40
# Vg_min = -Vg_max
# delta_Vg = 20
# Vg_list = np.arange(Vg_min, Vg_max, delta_Vg)

Vg_list = np.array([-40, -20, 0, 12, 20, 40])



''' Initialize '''
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
T = 5.9

# Keysight for IV
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeVoltage()
B2901A.write('SENS:CURR:PROT 0.01') #set the current compliance limit to 10mA
B2901A.SetOutputOn()

# Keysight for gating
B2961A = Keysight_B2961A('TCPIP::192.168.1.50::INSTR')
B2961A.SetModeVoltage()
B2961A.write('SENS:CURR:PROT 0.01') #set the current compliance limit to 10mA
B2961A.SetOutputOn()

## Output setting
idstring = '_at{:.2f}K'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'T (K)', 'Time (s)', 'Vg (V)', 'leakage current (I)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)


V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)


END = False




''' Start the measurement '''


## Ramping up the gate to the first point

last_time = time.time()




B2961A.RampVoltage(Vg_list[0],tt=10., steps = 100)  #biasing
B2901A.RampVoltage(V_bias_list[0],tt=5., steps = 10)  #biasing

palette = plt.get_cmap('Set1')
plt.rcParams["figure.figsize"] = [16,9]


## Sweeping the bias voltage
for Vg_count, Vg in enumerate (Vg_list):

    current_array = np.array([])
    VBias_array = np.array([])

    B2961A.SetVoltage(Vg)  #Setting the gate
    leakage_current = B2961A.GetCurrent()

    # plt.subplot(2, 1, 1)
    # plt.legend(['{:.1f}'.format(Vg)])

    # plt.subplot(2, 1, 2)
    # plt.legend(['{:.1f}'.format(Vg)])

    if END:
      break


    for count, V_bias in enumerate(V_bias_list):

        if END:
          break

        B2901A.SetVoltage(V_bias)  #biasing
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
        line = [V_bias, I, T, current_time - last_time, V_bias, leakage_current]
        stlab.writeline(myfile, line)

        myfile.write('\n')


        plt.subplot(2, 1, 1)
        plt.title(prefix)
        plt.ylabel('current [$\mu$A]')
        plt.xlim(V_bias_min*1e3,V_bias_max*1e3)
        if count ==0:
            plt.plot(VBias_array*1e3,current_array*1e6, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg), color=palette(Vg_count))
            plt.legend()

        else:
            plt.plot(VBias_array*1e3,current_array*1e6+1500*Vg_count, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, color=palette(Vg_count))



        if count > 0:
            plt.subplot(2, 1, 2)
            if count ==1:
                plt.plot(VBias_array[1:]*1e3,R_array, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg), color=palette(Vg_count))
                plt.legend()
            else:
                plt.plot(VBias_array[1:]*1e3,R_array+1500*Vg_count, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, color=palette(Vg_count))

            plt.xlabel('bias Voltage [mV]')
            plt.ylabel('dV/dI [$\Omega$]')

            plt.xlim(V_bias_min*1e3,V_bias_max*1e3)
            plt.ylim(0, 11000)

        plt.pause(0.1)








plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
B2901A.RampVoltage(0,tt=5, steps = 5)
B2961A.RampVoltage(0,tt=10, steps = 100)

B2901A.close()
B2961A.close()

myfile.close()

