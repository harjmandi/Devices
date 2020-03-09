''' This program uses HF2LI lock-in amplifier to measure the resistance of the sample while cooling. 
Optionally a constant gate Voltage can be applied using the KEYSIGHT B2901A. 
The program in the current version is suitable for cooling; small adjustmets are required to use it for warming up.


To avoid unneccesary data collection, different measurement intervals (set by measure_pattern_dt) are used at different temperature ranges (set by measure_pattern_T).
At each measurement time, the program measures the temperature and only if the delta T is large enough (set by measure_pattern_dT) it measures and records the resistance. 



Hardware to be used:
    - HF2LI: to measure the resistance of graphene device
    - A bias resistance of 1M: As voltage to current converter for lock-in out put.
        Note that there is always errors in reading the resitance of the device; the error is around -33% depending on the gain on S4c (see the excel file "Calibrate S4c gain.xlsx").

    - B2901A: For gating (Optional)

'''

import numpy as np
from stlab.devices.IVVI import IVVI_DAC
import time
import stlab
import stlabutils
import os
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math
from stlab.devices.He7Temperature import He7Temperature

def R_int(mode, gain): # This function estimates the expected internal resistance of the set up based on the formula provided http://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm1b.htm
    if mode == 'Low-Noise':
        R_int = 2000+ gain*1e-3
        
    if mode == 'Low-Rin':
        R_int = 2000+ gain*1e-4
        
    return R_int
    
#############################################################
''' Definitions'''

# IO
prefix = 'F18_e7_RvsT_'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F18 2020-02-18 measurements with LP filters/'

do_plot = True
save_data =True

V_bias = 30 # bias Voltage  [uV], The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
# 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.


# Gate settings 
gate = 0 # Choose 0 not to apply any gate
time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1.5 # the safe speed for ramping the gate voltage [V/s]
measure_leakage = False
measure_iteration = 2 #measure iteration for averaging 

# Temperature settings
measure_pattern_T = np.array([300, 150, 50, 10, 4]) # Different temperature ranges to set different measurement temperature steps
measure_pattern_dT = np.array([30, 10, 5, 0.1, 0.1]) # Temperature steps to run a resistance measurements
measure_pattern_dt = np.array([5*60, 2*60, 30, 10, 3]) # Time span between two subsequent temperature readings

# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 1e6  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 1 #postgain switch [x100ac x1 x100dc], set on M1b unit
M1b_mode = 'Low-Noise' # 'Low-Noise' or 'Low-Rin'

S1h_gain = 45. #V/V gain for the applied gate, set on S1h
S3b_range = 100e-6  #Full range of the applied current, set on S4c


M1b_total_gain = M1b_gain*M1b_postgain_switch
prefix =prefix+str(V_bias)+'uV'
V_bias *=1e-6

initial_calibration = True



##########################################################
''' Initializing the devices '''

##Inititalizing the IVVI
ivvi = IVVI_DAC(addr='COM4', verb=True)
ivvi.RampAllZero(tt=2., steps = 10)

## Temperature readout
tempdev = He7Temperature(addr='145.94.39.138',verb=False)


vmeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the voltage accross the sample


# IO settings
pygame.init()
pygame.display.set_mode((100,100))

#############################################################
''' MEASUREMENT'''

if save_data:
    colnames = ['time (s)','temperature (K)', 'gate voltage (V)','leakage current (A)','resistance (ohm)']
    my_file= stlab.newfile(prefix,'_',autoindex=True,colnames=colnames, mypath= path)


END = False
INI_time = time.time()
t0 = INI_time
T0 = 300

TIME = np.empty(shape=(0))
TEMPERATURE = np.empty(shape=(0))
RESISTANCE = np.empty(shape=(0))

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


leakage_current = 0
if gate != 0:
    print('############# Initialize back-gate to',gate,'V #############')
    ivvi.RampVoltage(S1h_dac,gate/S1h_gain*1000.,tt=gate/ramp_speed) ##ramping to the 
    print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(10,gate))
    time.sleep(10) 

    if measure_leakage:
        v_gateleakage = stlab.adi(addr='TCPIP::192.254.89.117::INSTR') #for measuring the leakage current
        leakage_current = float(v_gateleakage.query('READ?'))*1e-6



p = -1 #polarity of the bias voltage

while (not END):

    t =  time.time()-INI_time
    
    try: 
        T = tempdev.GetTemperature()
    except: 
        T = 300

    print ('Temp = ', T)

    ind = np.where(measure_pattern_T >= T)
    
    if np.abs(T0 - T) > measure_pattern_dT[ind[0][-1]]:
        print ('MEASUREING ...')

        I_p1 = 0
        I_p2 = 0
        

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


        line = [t,T, gate, leakage_current] + R
    
        if save_data:
            stlab.writeline(my_file,line)

        TEMPERATURE = np.append(TEMPERATURE,T)
        RESISTANCE = np.append(RESISTANCE,R)
        TIME = np.append(TIME,t)

        plt.rcParams["figure.figsize"] = [16,9]


        plt.subplot(2, 1, 1)
        plt.plot(TEMPERATURE,RESISTANCE, '--b',marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)

        plt.ylabel('Resistance ($\Omega$)')
        plt.xlim(np.min(TEMPERATURE),np.max(TEMPERATURE))
        plt.title(prefix)


        plt.subplot(2, 1, 2)
        
        plt.plot(TEMPERATURE,RESISTANCE/1000, '--b', marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)
        plt.ylabel('resistance (k$\Omega$)')
        plt.xlim(np.min(TEMPERATURE),np.max(TEMPERATURE))


        plt.plot(TEMPERATURE[:-1], np.diff(RESISTANCE)/np.diff(TEMPERATURE), '--b', marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)
        plt.xlabel('Temperature (K)')
        plt.xlim(np.min(TEMPERATURE),np.max(TEMPERATURE))
        plt.ylim(0, 200)

        plt.ylabel('$\Delta$R/$\Delta$T ($\Omega/K$)')

        plt.pause(0.1)
        T0 = T

    else: 
        print('Elapsed time: {:.0f} min'.format((time.time()-t0)/60))
        print('Waitng the temperature to fall below {:.2f} ...'.format(T0 - measure_pattern_dT[ind[0][-1]]))
        print('Measuring every {:.0f}s'.format(measure_pattern_dt[ind[0][-1]]))


    
    while (time.time()-t0 < measure_pattern_dt[ind[0][-1]]) and (not END):

        for event in pygame.event.get():
            if event.type == QUIT: sys.exit()
            elif event.type == KEYDOWN and event.dict['key'] == 101:
                END = True
                print ('END command detected ...')

        

    t0 = time.time()


print('MEASUREMENT FINISHED')
if gate != 0: ivvi.RampVoltage(S1h_dac,0.,tt=30.) 

ivvi.RampAllZero(tt=2.)
vmeas.close()
ivvi.close()



#######################################################################
''' saving the data '''


if save_data:

    # saving the metafile
    plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
    my_file.close()



