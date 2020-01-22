''' This program uses IVVI S1H to apply a gate voltage and S3b as a Voltage bias to measure the resistance of the sample
- To compensate for the internal resistances of the source and measure units, the program starts with a calibration with no sample (R sample = 0)
- To compensate for the ofset of the voltgae measurement, two current measurements (I_p, I_n) at positive and negative bias Voltages (V_n = -V_p) are perfomred
and resistance is measured using R = 2*V_n/(I_p-I_n)


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
import os
import sys



''' input ''' 
prefix = 'F17_IV_8fg_VBias'

V_bias_max = 300e-6 # [uV] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[uV], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/100 #[uV]

Vgmax = 2 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 0.1 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
time_sleep = 10 #sleep time to stablize the gate [s], proposed: 5

# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 1e6  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 1 #postgain switch [x100ac x1 x100dc], set on M1b unit
S1h_gain = 45. #V/V gain for the applied gate, set on S1h
S3b_range = 1e-3  #Full range of the applied current, set on S4c

M1b_total_gain = M1b_gain*M1b_postgain_switch


''' Check for errors '''
EXIT = False
if V_bias_max > S3b_range:
    print ('Maximum bias voltage exceeds the range on S3b.')
    EXIT = True

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

## Output setting
idstring = '_at{:.2f}mK'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)


Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
Vg_ini = Vglist[0]

V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)

END = False

plt.rcParams["figure.figsize"] = [16,9] 
plt.title(prefix)
plt.ylabel('current [nA]')
plt.xlabel('bias Voltage [$\mu$V]')
plt.xlim(V_bias_min*1e6,V_bias_max*1e6)
palette = plt.get_cmap('Set1') # create a color palette


##Inititalizing the devices
ivvi = IVVI_DAC(addr='COM5', verb=True)
ivvi.RampAllZero(tt=2., steps = 20)

Imeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the current converted to Voltage at M0 output
v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current


''' Start the measurement '''


## Ramping up the gate to the first point 
print('############# Initialize back-gate to',Vg_ini,'V #############')
ivvi.RampVoltage(S1h_dac,Vg_ini/S1h_gain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(time_sleep,Vg_ini))
time.sleep(time_sleep) 
last_time = time.time()


## Sweeping the gate
for gate_count,Vg in enumerate(Vglist):
    
    ivvi.RampVoltage(S1h_dac,Vg/S1h_gain*1000.,tt=deltaVg/gate_ramp_speed, steps = 3) ##ramping this gate voltage
    print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep, Vg))
    time.sleep(time_sleep)
    I_leakage = float(v_gateleakage.query('READ?'))*1e3 #the factor 1e3 is used to convert the current to [nA]

    try:
        T = mytriton.GetTemperature(8)
    except:
        T = -1
    current_array = []

    ivvi.RampVoltage(S3b_dac, V_bias_list[0]/S3b_range*1e3,tt=1., steps = 10)  #biasing at reverse Voltage   


    ## Sweeping the bias voltage
    for V_bias in V_bias_list: 

        for event in pygame.event.get():
          if event.type == QUIT:sys.exit()
          elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
            END = True

        if END:
          break
               
        ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.1, steps = 5)  #biasing at reverse Voltage   
        I = float(Imeas.query('READ?')) / M1b_total_gain

        current_array = np.append(current_array,I) 

        current_time = time.time()
        line = [V_bias, I, Vg, T, current_time - last_time, I_leakage]
        stlab.writeline(myfile, line)
        
        myfile.write('\n')
        # stlab.metagen.fromarrays(myfile, Vglist, range(count+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)
    

    plt.plot(V_bias_list*1e6,current_array*1e9, '--r', marker='o', color=palette(gate_count), linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
    plt.legend()
    plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(S1h_dac,0.,tt=30.) 
ivvi.RampAllZero(tt=5.)
Imeas.close()
ivvi.close()


myfile.close()
