'''

'''



import stlab
import stlabutils
import numpy as np
import time
import datetime
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
from matplotlib.pyplot import subplots, show
from stlab.devices.Keysight_B2901A import Keysight_B2901A
from stlab.devices.keysightB2961A import keysightB2961A as Keysight_B2961A
from ipywidgets import interactive
from IPython.display import display
import os
import sys
import matplotlib.gridspec as gridspec



''' input '''
prefix = 'F20_IV_h3-3to4-floating12_VBias_B2901'
path = 'D:/measurement_data_4KDIY/Hadi/F20 2020-05-11 measurements/'


V_bias_max = 1.5 #[V] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[V], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/625 # V_bias_max/80 #[V]
average_I = 3 #number of current measurement per Voltage point
bias_measure_sleep = 0.05 # sleep time between each current measurement
bias_step_sleep = 0.1 # sleep time to stablize bias voltage
V_bias_list = np.linspace(V_bias_max, V_bias_min, int((V_bias_max-V_bias_min)/delta_V_bias)+1)


Vg_max = 42
Vg_min = -20

delta_Vg = 0.5
Vg_list = np.arange(Vg_min, Vg_max, delta_Vg)



''' Initialize '''
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
T = 5.85

# Keysight for IV
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeVoltage()
B2901A.write('SENS:CURR:PROT 0.01') #set the current compliance limit to 10mA
B2901A.SetOutputOn()

# Keysight for gating
B2961A = Keysight_B2961A('TCPIP::192.168.1.50::INSTR')
B2961A.SetModeVoltage()
# B2961A.write('SENS:CURR:PROT 0.0001') #set the current compliance limit to 100uA
B2961A.SetComplianceCurrent(20e-9)
B2961A.SetOutputOn()

## Output setting
idstring = '_at{:.2f}K'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'R (Ohm)', 'T (K)', 'Vg_set (V)', 'Vg_actual (V)','leakage current (I)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)
stlab.metagen.fromarrays(myfile,V_bias_list,Vg_list,zarray=[],xtitle='bias Voltage (V)',ytitle='gate Voltage (V)',ztitle='',colnames=colnames)




END = False


''' Start the measurement '''


## Ramping up the gate to the first point

start_time = time.time()

B2961A.RampVoltage(Vg_list[0],tt=60., steps = 100)  #gating
B2901A.RampVoltage(V_bias_list[0],tt=5., steps = 10)  #biasing

plt.rcParams["figure.figsize"] = [16,9]
fig, (ax1,ax2, ax3)= subplots(3, 1, sharex = True)

## Sweeping the bias voltage
for Vg_count, Vg in enumerate (Vg_list):

    current_array = np.array([])
    VBias_array = np.array([])
    R_array = np.array([])

    B2961A.RampVoltage(Vg,tt=2, steps = 10)  #Setting the gate
    Vg_actual = B2961A.GetVoltage()
    leakage_current = B2961A.GetCurrent()

    for count, V_bias in enumerate(V_bias_list):

        B2901A.SetVoltage(V_bias)  #biasing
        time.sleep(bias_step_sleep)

        I = 0
        for i in range (average_I):
            for event in pygame.event.get():
              if event.type == QUIT:sys.exit()
              elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
                END = True
                B2901A.RampVoltage(0,tt=60, steps = 20)
                B2961A.RampVoltage(0,tt=60, steps = 100)

            if END:
              break


            I += B2901A.GetCurrent()
            time.sleep(bias_measure_sleep)

        if END:
            break

        I = I/average_I
        current_array = np.append(current_array,I)
        VBias_array = np.append(VBias_array,V_bias)
        R_array = np.diff(VBias_array)/np.diff(current_array)

        line = [V_bias, I, V_bias/I, T,  Vg, Vg_actual, leakage_current]
        stlab.writeline(myfile, line)



    if END:
      break

    if Vg_count == 0:
        R_map = R_array
    else:
        R_map = np.vstack((R_map,R_array))

    elapsed_time = time.time()- start_time
    remaning_time = (Vg_list.size-Vg_count-1)*elapsed_time/(Vg_count+1)

    ax1.cla()
    ax1.set_title(prefix)
    ax1.set_ylabel('current [$\mu$A]')
    ax1.plot(VBias_array*1e3,current_array*1e6, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg_actual))
    ax1.legend()

    ax2.cla()
    ax2.plot(VBias_array[1:]*1e3,R_array, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg_actual))
    ax2.legend()
    ax2.set_ylabel('dV/dI [$\Omega$]')
    ax2.set_ylim([0, 4000])


    if Vg_count > 0:
        extent = [V_bias_min*1e3,V_bias_max*1e3, Vg_list[0], Vg_list[Vg_count]]
        ax3.imshow(R_map, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = 0, vmax = 2000)

    ax3.set_title('Elapsed time: '+ str(datetime.timedelta(seconds=elapsed_time)).split(".")[0]+ ',    remaning time: <'+ str(datetime.timedelta(seconds=remaning_time)).split(".")[0] )
    ax3.set_ylabel('$V_g$ (V)')
    ax3.set_xlabel('bias Voltage (mV)')
    ax3.set_xlim([V_bias_min*1e3,V_bias_max*1e3])


    plt.pause(0.05)



plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
B2901A.RampVoltage(0,tt=10, steps = 20)
B2961A.RampVoltage(0,tt=10, steps = 100)

B2901A.close()
B2961A.close()

myfile.close()

