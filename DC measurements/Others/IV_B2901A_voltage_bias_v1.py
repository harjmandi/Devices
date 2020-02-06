''' This program uses IVVI S1H to apply a gate voltage and S3b as a Voltage bias to measure the current through of the sample
-
  Hardware to be used: 
    - IVVI S1h: For gating
    - IVVI S3b: As the Voltage source
    - IVVI M1b: for current measurement
    - IVVI M0: convert current measurement into Voltage
    
    - Keithley 2000 or DMM6500:  to measure the voltage drop accross the sample
    - Keithley 2000 or DMM6500:  to measure the leakacge current

    - TritonWrapper: to measure the temperature of the fridge
  

 
'''



import stlab
import stlabutils
from stlab.devices.IVVI import IVVI_DAC
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
prefix = 'F17_IV_h12_VBias_10mV'


V_bias_max = 10e-3 # [uV] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[uV], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/200 #[uV]
average_I = 10 #number of current measurement per Voltage point
bias_time_sleep = 0.2 # sleep time between each current measurement

Vgmax = 0 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 0.1 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
gate_time_sleep = 10 #sleep time to stablize the gate [s], proposed: 5

# DACs
S1h_dac = 1 #DAC number for gate voltage

# gains
S1h_gain = 15. #V/V gain for the applied gate, set on S1h

''' Check for errors '''
EXIT = False


if Vgmax > 2*S1h_gain:
    print ('Maximum gate voltage exceeds the range on S1h.')
    EXIT = True

if EXIT:
    sys.exit(0)


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
colnames = ['Vset (V)', 'Imeas (A)', 'Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)


Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)

if Vgmax ==Vgmin == 0:
    gate_it =False
else: 
    gate_it =True


if gate_it: 
    ##Inititalizing the devices
    ivvi = IVVI_DAC(addr='COM5', verb=True)
    ivvi.RampAllZero(tt=2., steps = 20)
    v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current


Vg_ini = Vglist[0]

V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)

END = False

plt.rcParams["figure.figsize"] = [16,9] 
plt.title(prefix)
plt.ylabel('current [nA]')
plt.xlabel('bias Voltage [$\mu$V]')
plt.xlim(V_bias_min*1e6,V_bias_max*1e6)
palette = plt.get_cmap('Set1') # create a color palette


''' Start the measurement '''


## Ramping up the gate to the first point
if Vg_ini !=0:
    print('############# Initialize back-gate to',Vg_ini,'V #############')
    ivvi.RampVoltage(S1h_dac,Vg_ini/S1h_gain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
    print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(gate_time_sleep,Vg_ini))
    time.sleep(gate_time_sleep) 
last_time = time.time()


## Sweeping the gate
for gate_count,Vg in enumerate(Vglist):
    
    if Vg !=0:
        ivvi.RampVoltage(S1h_dac,Vg/S1h_gain*1000.,tt=deltaVg/gate_ramp_speed, steps = 3) ##ramping this gate voltage
        print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(gate_time_sleep, Vg))
        time.sleep(gate_time_sleep)
        I_leakage = float(v_gateleakage.query('READ?'))*1e3 #the factor 1e3 is used to convert the current to [nA]
    else: I_leakage = 0

    try:
        T = mytriton.GetTemperature(8)
    except:
        T = -1
    current_array = []

    B2901A.RampVoltage(V_bias_list[0],tt=5., steps = 10)  #biasing    


    ## Sweeping the bias voltage
    for V_bias in V_bias_list: 

        for event in pygame.event.get():
          if event.type == QUIT:sys.exit()
          elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
            END = True

        if END:
          break
               
        B2901A.RampVoltage(V_bias,tt=1, steps = 5)  #biasing at reverse Voltage   
        I = 0
        for i in range (average_I):
            I += B2901A.GetCurrent()
            time.sleep(bias_time_sleep)

        current_array = np.append(current_array,I/average_I) 

        current_time = time.time()
        line = [V_bias, I, Vg, T, current_time - last_time, I_leakage]
        stlab.writeline(myfile, line)
        
        myfile.write('\n')
    

    plt.plot(V_bias_list*1e6,current_array*1e9, '--',marker='.',markersize=1.5, color=palette(gate_count), linewidth=0.15, alpha=0.9, label='{:.0f}Vg'.format(Vg))

    plt.legend()
    plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
B2901A.close()

myfile.close()
if gate_it:
    v_gateleakage.close()
    ivvi.RampVoltage(S1h_dac,0.,tt=30.) 
    ivvi.RampAllZero(tt=5.)
    ivvi.close()
