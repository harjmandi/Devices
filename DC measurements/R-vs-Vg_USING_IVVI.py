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


'''



import stlab
import stlabutils
from stlab.devices.IVVI import IVVI_DAC
# from stlab.devices.TritonWrapper import TritonWrapper
import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
import os
import sys


def R_int(mode, gain): # This function estimates the expected internal resistance of the set up based on the formula provided http://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm1b.htm
    if mode == 'Low-Noise':
        R_int = 2000+ gain*1e-3
        
    if mode == 'Low-Rin':
        R_int = 2000+ gain*1e-4
        
    return R_int


''' input ''' 
prefix = 'F18_e7_FE_IVVI_VBias_250mK_'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F18 2020-03-04 measurements with LP filters/'

V_bias = 100 # bias Voltage  [uV], The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
# 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.

Vgmax = 65 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 1 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
time_sleep = 0.5 #sleep time to stablize the gate [s], proposed: 2
measure_leakage = False
measure_iteration = 2 #measure iteration for averaging 


# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 1e9  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 1 #postgain switch [x100ac x1 x100dc], set on M1b unit
M1b_mode = 'Low-Noise' # 'Low-Noise' or 'Low-Rin'

S1h_gain = 45. #V/V gain for the applied gate, set on S1h
S3b_range = 100e-6  #Full range of the applied current, set on S4c


M1b_total_gain = M1b_gain*M1b_postgain_switch
prefix =prefix+str(V_bias)+'uV'
V_bias *=1e-6

initial_calibration = True # initial calibration to estimate the internal resisatnces of the components. 
# Alternatively the internal resistance can be calculated using the formula provided http://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm1b.htm

# Temperature
T = 75


''' Initialize '''  
pygame.init()
pygame.display.set_mode((100,100))


## Output setting
idstring = '_at{:.2f}mK'.format(T).replace('.','p')
colnames = ['Vmeas (V)', 'Iset+ (A)', 'Iset- (A)','Resistance (ohm)', 'gate voltage (V)', 'T (K)', 'Time (s)', 'leakage current (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)

Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
Vg_ini = Vglist[0]
END = False
total_count = Vglist.shape[0]
resistance_array = np.array([])
applied_gate_array = np.array([])
Iset_p_array = np.array([])
Iset_n_array = np.array([])



##Inititalizing the devices
ivvi = IVVI_DAC(addr='COM4', verb=True)
ivvi.RampAllZero(tt=2., steps = 10)

vmeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the voltage accross the sample


if measure_leakage:
    v_gateleakage = stlab.adi(addr='TCPIP::192.254.89.117::INSTR') #for measuring the leakage current
I_leakage = 0

## Estimating for the internal resistances
if initial_calibration:
    I_cal_p = 0
    I_cal_n = 0
    print ('#### Calibration for the internal resistances ####')
    input ('Short the S3b_output and M1b_input (pin #4), Press Enter to continue...')
    ivvi.RampVoltage(S3b_dac,V_bias/S3b_range*1e3,tt=0.5, steps = 5) ##ramping this voltage in 20seconds
    
    for cnt in range (measure_iteration):
        I_cal_p += float(vmeas.query('READ?')) / M1b_total_gain

    I_cal_p = I_cal_p/measure_iteration

    ivvi.RampVoltage(S3b_dac,-V_bias/S3b_range*1e3,tt=1, steps = 5) ##ramping this voltage in 20seconds

    for cnt in range (measure_iteration):
        I_cal_n += float(vmeas.query('READ?')) / M1b_total_gain

    I_cal_n = I_cal_n/measure_iteration
    
    R_cal = 2*V_bias/(I_cal_p-I_cal_n)

    print ('V_bias:',V_bias)
    print('I_cal_p:',I_cal_p)
    print('I_cal_n',I_cal_n)

    print ('#### Calibration finished ####')
    print ('Total internal resistance measures: {:.2f}kOhm'.format(R_cal/1000))
    print ('Expected internal resistance is {:.2f}kOhm'.format(1e-3*R_int(M1b_mode, M1b_gain)))
    h = input ('Connect to the device, Press Enter to continue, press "e" to exit.' )

    if h == "e":
        sys.exit(0)

else: 
    R_cal = R_int(M1b_mode, M1b_gain)
    ivvi.RampVoltage(S3b_dac,-V_bias/S3b_range*1e3,tt=1, steps = 5) ##ramping this voltage in 20seconds



## Ramping up the gate
print('############# Initialize back-gate to',Vg_ini,'V #############')
ivvi.RampVoltage(S1h_dac,Vg_ini/S1h_gain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(5*time_sleep,Vg_ini))
time.sleep(5*time_sleep) 



## Start the measurement
p = -1 #polarity of the bias voltage


last_time = time.time()
for count,Vg in enumerate(Vglist):
    for event in pygame.event.get():
      if event.type == QUIT:sys.exit()
      elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
        END = True

    if END:
      break

    ivvi.RampVoltage(S1h_dac,Vg/S1h_gain*1000.,tt=deltaVg/gate_ramp_speed, steps = 3) ##ramping this gate voltage
    print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep, Vg))
    time.sleep(time_sleep) 
        
    I_p1 = 0
    I_p2 = 0
    
    # ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.5, steps = 3)  #biasing at reverse Voltage   
    # time.sleep(10) 


    for cnt in range (measure_iteration):
        I_p1 += float(vmeas.query('READ?')) / M1b_total_gain
        time.sleep(0.1)

    
    I_p1 = I_p1/measure_iteration
    

    p*=-1
    ivvi.RampVoltage(S3b_dac, p*V_bias/S3b_range*1e3,tt=0.5, steps = 3)  #biasing at reverse Voltage   
    
    time.sleep(1) 

    for cnt in range (measure_iteration):
        I_p2 += float(vmeas.query('READ?')) / M1b_total_gain
        time.sleep(0.1)

    I_p2 = I_p2/measure_iteration


    if p == -1: 
        I_p1, I_p2 = I_p2, I_p1

    print('V_bias=', V_bias)
    print ('I_p1 = ', I_p1)
    print('I_p2 = ', I_p2)
    print ('R_cal = ', R_cal)

    R = (2*V_bias/np.absolute(I_p1-I_p2))-R_cal
    print ('R = ', R)
    print ('#####################################')

    if measure_leakage:
        I_leakage = float(v_gateleakage.query('READ?'))*1e3 #leakage current [nA]

    resistance_array = np.append(resistance_array,R)
    applied_gate_array = np.append(applied_gate_array,Vg)
    Iset_p_array = np.append(Iset_p_array,I_p2)
    Iset_n_array = np.append(Iset_n_array,I_p1)

    current_time = time.time()
    line = [V_bias, I_p2, I_p1, R, Vg, T, current_time - last_time, I_leakage]
    stlab.writeline(myfile, line)
    
    myfile.write('\n')
    stlab.metagen.fromarrays(myfile, Vglist, range(count+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)

     
    plt.rcParams["figure.figsize"] = [16,9] 
    plt.subplot(2, 1, 1) 
    plt.plot(applied_gate_array,resistance_array*1e-3, '--r', marker='.', linewidth = 0.5)
    plt.title(prefix)
    plt.ylabel('resistance [$k\Omega$]')
    # plt.ylim(0,8)
    plt.xlim(Vgmin,Vgmax)

    
    plt.subplot(2, 1, 2)
    plt.plot(applied_gate_array,1e9*Iset_p_array, '--r', marker='.', linewidth = 0.5) 
    plt.plot(applied_gate_array,1e9*Iset_n_array, '--b', marker='.', linewidth = 0.5) 

    plt.ylabel('bias current [nA]') 
    plt.xlabel('gate voltage  [V]')
    plt.xlim(Vgmin,Vgmax)


    plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(S1h_dac,0.,tt=30.) 
ivvi.RampAllZero(tt=2.)
vmeas.close()
ivvi.close()

myfile.close()

title = 'Resistance'
caption = ''
stlab.autoplot(myfile,'gate voltage (V)','Resistance (ohm)',title=title,caption=caption)

title = 'Leakage Current'
caption = ''
stlab.autoplot(myfile,'gate voltage (V)','leakage current (nA)',title=title,caption=caption)

