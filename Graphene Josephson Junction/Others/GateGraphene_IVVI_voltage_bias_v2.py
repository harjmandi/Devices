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



''' input ''' 
prefix = 'F17_FE_8cd_VBias_'

V_bias = 50 # bias Voltage  [uV], The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
# 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.

Vgmax = 65 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 1 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
time_sleep = 0.5 #sleep time to stablize the gate [s], proposed: 2

# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 10e6  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 1 #postgain switch [x100ac x1 x100dc], set on M1b unit
S1h_gain = 45. #V/V gain for the applied gate, set on S1h
S3b_range = 100e-6  #Full range of the applied current, set on S4c



M1b_total_gain = M1b_gain*M1b_postgain_switch

prefix =prefix+str(V_bias)+'uV'
V_bias *=1e-6



plt.title(prefix+'$I_{max}$:{:.1f}nA, $I_{mmin}$:{:.1f}nA'.fomrat(1e-9*V_bias/np.Minimum(resistance_array),1e-9*V_bias/np.Maximum(resistance_array)))







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
colnames = ['Vmeas (V)', 'Iset (A)', 'Rmeas (Ohm)', 'Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)


Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
Vg_ini = Vglist[0]
END = False
total_count = Vglist.shape[0]
resistance_array = np.array([])
applied_gate_array = np.array([])
I_leakage_array = np.array([])


##Inititalizing the devices
ivvi = IVVI_DAC(addr='COM5', verb=True)
ivvi.RampAllZero(tt=2.)

vmeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the voltage accross the sample
v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current

## Estimating for the internal resistances
print ('#### Calibration for the internal resistances ####')
input ('Short the S3b_output and M1b_input (pin #4), Press Enter to continue...')

ivvi.RampVoltage(S3b_dac,V_bias/S3b_range*1e3,tt=0.5, steps = 5) ##ramping this voltage in 20seconds
I_cal_p = float(vmeas.query('READ?')) / M1b_total_gain

ivvi.RampVoltage(S3b_dac,-V_bias/S3b_range*1e3,tt=1, steps = 5) ##ramping this voltage in 20seconds
I_cal_n = float(vmeas.query('READ?')) / M1b_total_gain

R_cal = 2*V_bias/(I_cal_p-I_cal_n)

print ('V_bias:',V_bias)
print('I_cal_p:',I_cal_p)
print('I_cal_n',I_cal_n)

print ('#### Calibration finished ####')
print ('Total internal resistance measures: {:.2f}kOhm'.format(R_cal/1000))
input ('Connect to the device, Press Enter to continue...')


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
        
    I_p1 = float(vmeas.query('READ?')) / M1b_total_gain
    ivvi.RampVoltage(S3b_dac, -p*V_bias/S3b_range*1e3,tt=1., steps = 5)  #biasing at reverse Voltage   
    I_p2 = float(vmeas.query('READ?')) / M1b_total_gain
    p*=-1
    R = (2*V_bias/np.absolute(I_p1-I_p2))-R_cal

    I_leakage = float(v_gateleakage.query('READ?'))*1e3 #leakage current [nA]

    resistance_array = np.append(resistance_array,R)
    applied_gate_array = np.append(applied_gate_array,Vg)
    I_leakage_array = np.append(I_leakage_array,I_leakage)

    current_time = time.time()
    line = [V_bias, np.absolute(I_p1-I_p2), R, Vg, T, current_time - last_time, I_leakage]
    stlab.writeline(myfile, line)
    
    myfile.write('\n')
    stlab.metagen.fromarrays(myfile, Vglist, range(count+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)

    plt.rcParams["figure.figsize"] = [16,9] 
    plt.subplot(2, 1, 1) 
    plt.plot(applied_gate_array,resistance_array, '--r', marker='o')
    plt.title(prefix+'$I_{max}$:{:.1f}nA, $I_{mmin}$:{:.1f}nA'.fomrat(1e-9*V_bias/np.Minimum(resistance_array),1e-9*V_bias/np.Maximum(resistance_array)))
    plt.ylabel('resistance [$\Omega$]')
    plt.xlim(Vgmin,Vgmax)

    
    plt.subplot(2, 1, 2)
    plt.plot(applied_gate_array,I_leakage_array, '--r', marker='o') 
    plt.ylabel('leakage current [nA]') 
    plt.xlabel('gate voltage  [V]')
    plt.xlim(Vgmin,Vgmax)


    plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(S1h_dac,0.,tt=30.) 
ivvi.RampAllZero(tt=5.)
vmeas.close()
ivvi.close()


myfile.close()
