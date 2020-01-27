''' This program uses IVVI S1H to apply a gate voltage and S3b as a Voltage bias to measure the resistance of the sample


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
from stlab.devices.He7Temperature import He7Temperature




''' input ''' 
prefix = 'F17_IV_8ab_VBias'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F17 2020-01-22 measurements/')


V_bias_max = 5e-3 # [V] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[V], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
delta_V_bias = V_bias_max/200 #[V]
measure_average = 20 # number of the measurements per each bias Voltage for averaging
time_sleep_measure = 0.1 # sleep time in between measurements
calibrate = False # Calibrate for the internal resistances of the measurement units

Vgmax = 0 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 0.1 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
time_sleep_gate = 10 #sleep time to stablize the gate [s], proposed: 5
measure_gate_leakage = False 

# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 1e6  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 1 #postgain switch [x100ac x1 x100dc], set on M1b unit
S1h_gain = 45. #V/V gain for the applied gate, set on S1h
S3b_range = 10e-3  #Full range of the applied current, set on S4c

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
    T = He7Temperature(addr='145.94.39.138',verb=False).GetTemperature()
except:
    T = -1

## Output setting
idstring = '_at{:.2f}mK'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)


Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
if Vgmax == Vgmin:
    Vglist =[Vgmax]

Vg_ini = Vglist[0]

V_bias_list = np.linspace(V_bias_max, V_bias_min, (V_bias_max-V_bias_min)/delta_V_bias+1)

END = False

plt.rcParams["figure.figsize"] = [16,9] 
palette = plt.get_cmap('Set1') # create a color palette


##Inititalizing the devices
ivvi = IVVI_DAC(addr='COM4', verb=True)
ivvi.RampAllZero(tt=2., steps = 20)

Imeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the current converted to Voltage at M0 output

if Vgmax !=0 and measure_gate_leakage:
    v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current
else:
    I_leakage = -1

''' Start the measurement '''


## Ramping up the gate to the first point 
if Vgmax !=0:
    print('############# Initialize back-gate to',Vg_ini,'V #############')
    ivvi.RampVoltage(S1h_dac,Vg_ini/S1h_gain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the Vg_ini 
    print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(time_sleep_gate,Vg_ini))
    time.sleep(time_sleep_gate) 
last_time = time.time()

## Calibration for internal resistors

if calibrate:
    I_cal = [] 
    print('Calibration for internal resistances:')
    input('Please short the S3b output and M1b input, press ENTER to continue ...')

    for V_bias in V_bias_list: 
        ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.1, steps = 5)  #biasing at reverse Voltage   
        i_cal = 0
        for cnt in range(measure_average):
            i_cal += float(Imeas.query('READ?')) / M1b_total_gain
            time.sleep(time_sleep_measure)
        I_cal = np.append(I_cal,i_cal/measure_average)

    R_int = np.average(np.diff(V_bias_list)/np.diff(I_cal))
    print ('Calibration Finished: total internal resistance is {:.1f}kOhms.'.format(R_int/1000))
    input('Connect to the device and press ENTER to continue ...')



## Sweeping the gate
r_max = 0

ivvi.RampVoltage(S3b_dac, V_bias_list[0]/S3b_range*1e3,tt=5, steps = 5)  #ramping up to the first bias point   

for gate_count,Vg in enumerate(Vglist):
    
    if Vgmax !=0:
        ivvi.RampVoltage(S1h_dac,Vg/S1h_gain*1000.,tt=deltaVg/gate_ramp_speed, steps = 3) ##ramping this gate voltage
        print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep_gate, Vg))
        time.sleep(time_sleep_gate)

        if measure_gate_leakage:
            I_leakage = float(v_gateleakage.query('READ?'))*1e3 #the factor 1e3 is used to convert the current to [nA]
        else: 
            I_leakage = -1
    
    try:
        T = mytriton.GetTemperature(8)
    except:
        T = -1
    current_array = []
    V_bias_array = []


    ## Sweeping the bias voltage
    
    for count, V_bias in enumerate(V_bias_list): 

        for event in pygame.event.get():
          if event.type == QUIT:sys.exit()
          elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
            END = True

        if END:
          break
               
        ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.1, steps = 5)  #biasing    
        
        I_tot = 0
        for cnt in range(measure_average):
            I_tot += float(Imeas.query('READ?')) / M1b_total_gain
            time.sleep(time_sleep_measure)

        I_tot = I_tot/measure_average
        
        if calibrate:
            I = I_cal[count]*I_tot/(I_cal[count]-I_tot)
        else: 
            I = I_tot
        
        current_array = np.append(current_array,I) 
        V_bias_array = np.append(V_bias_array,V_bias) 

        r = np.diff(V_bias_array)/np.diff(current_array)
        
        if count > 0: r_max = np.max(r)

        current_time = time.time()
        line = [V_bias, I, Vg, T, current_time - last_time, I_leakage]
        stlab.writeline(myfile, line)
        
        myfile.write('\n')
        # stlab.metagen.fromarrays(myfile, Vglist, range(count+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)
    
        if Vgmax == Vgmin:
            plt.subplot(2,1,1)
            plt.title(prefix)

            plt.plot(V_bias_array*1e6,current_array*1e9, '--r', marker='.', linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
            plt.ylabel('current [nA]')
            if calibrate: plt.ylim(0, np.max(current_array)*1.05e9)
            plt.xlim(V_bias_min*1e6,V_bias_max*1e6)


            plt.subplot(2,1,2)
            plt.plot((V_bias_array[1:]+delta_V_bias/2)*1e6,r, '--r', marker='.', linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
            if calibrate: plt.ylim(0,1.1*r_max)
            plt.ylabel('dV/dI [$\Omega$]')
            plt.xlabel('bias Voltage [$\mu$V]')
            plt.xlim(V_bias_min*1e6,V_bias_max*1e6)



            plt.pause(0.1)



    if Vgmax != Vgmin:
        plt.subplot(2,1,1)
        plt.title(prefix)

        plt.plot(V_bias_list*1e6,current_array*1e9, '--r', marker='.', color=palette(gate_count), linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
        plt.legend()
        plt.ylabel('current [nA]')
        if calibrate:plt.ylim(0, np.max(current_array)*1.05e9)
        plt.xlim(V_bias_min*1e6,V_bias_max*1e6)



        plt.subplot(2,1,2)
        plt.plot((V_bias_array[1:]+delta_V_bias/2)*1e6,np.diff(V_bias_array)/np.diff(current_array), '--r', marker='.', linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
        plt.legend()             
        if calibrate: plt.ylim(0,1.1*r_max)
        plt.ylabel('dV/dI [$\Omega$]')
        plt.xlabel('bias Voltage [$\mu$V]')




        plt.pause(0.1)



plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
if Vgmax !=0:
    ivvi.RampVoltage(S1h_dac,0.,tt=30.) 
ivvi.RampAllZero(tt=5.)
Imeas.close()
ivvi.close()

if Vgmax !=0 and measure_gate_leakage:
    v_gateleakage.close()

myfile.close()
