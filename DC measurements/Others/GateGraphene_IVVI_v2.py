''' This program uses IVVI S1H to apply a gate voltage and S4c as a current bias to measure the resistance of the sample
The measurement bias current is fixed; suitable for graphene JJ. 



  Hardware to be used: 
    - IVVI DAC (S1h): For gating
    - IVVI DAC (S4c): As the current source. 
    
    - Keithley 2000 or DMM6500:  to measure the voltage drop accross the sample
    - Keithley 2000 or DMM6500:  to measure the leakacge current

    - TritonWrapper: to measure the temperature of the fridge
  


  Before runnign the programm: 
    - Make sure that in S2d, the appropriate DAC (in cyurrent version, DAC 1) is set to S1h.
    - Make sure that in S2d, the appropriate connection between Dual iso-in (Iso-Amp1) and S4c (E1) is made. 
    - Set an appropriate gain on S1h and M2m

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
prefix = 'F17_FE_e6_0102_2probe_biasI100nA'

i = 1e-9 # Bias current [A]


Vgmax = 50 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 0.5 # Gate voltage steps [V]
gate_ramp_speed = 0.3 # Gate ramp speed [V/s], proposed: 0.1
time_sleep = 1 #sleep time to stablize the gate [s], proposed: 2

# DACs
vgdac = 1 #DAC number for gate voltage
isdac = 3  #DAC number for current source

# gains
vmgain = 10000  #V/V gain for vmeas set on M2m unit
vggain = 45. #V/V gain for the applied gate, set on S1h
isgain = 1e-9  #Full range of the applied current, set on S4c



''' Initialize '''  
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
mytriton = TritonWrapper()
T = mytriton.GetTemperature(8)

print('### Measure T 10 times ###')

T0 = 0
for x in range(10):
    try:
        T = mytriton.GetTemperature(8)
    except:
        T = -1
    T0 += T
Tini = T0/10.*1000.
T= Tini
##Communicate with devices
ivvi = IVVI_DAC(addr='COM5', verb=True)
ivvi.RampAllZero(tt=10.)

vmeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the voltage accross the sample
v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current


idstring = '_at{:.2f}mK'.format(Tini).replace('.','p')
colnames = ['Iset (A)', 'Vmeas (V)', 'Rmeas (Ohm)', 'Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
last_time = time.time()

Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
Vg_ini = Vglist[0]
print('############# Initialize back-gate to',Vg_ini,'V #############')
ivvi.RampVoltage(vgdac,Vg_ini/vggain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(5*time_sleep,Vg_ini))
time.sleep(5*time_sleep) 

myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)
END = False
total_count = Vglist.shape[0]

ivvi.RampVoltage(isdac, i / isgain * 1e3,tt=10.)  #biasing current
resistance_array = np.array([])
applied_gate_array = np.array([])
I_leakage_array = np.array([])

for count,Vg in enumerate(Vglist):
    ivvi.RampVoltage(vgdac,Vg/vggain*1000.,tt=deltaVg/gate_ramp_speed, steps = 10) ##ramping this voltage in 20seconds
    print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep, Vg))
    print('Time remaining: {:.0f} min'.format((total_count-count)*(time_sleep+deltaVg/gate_ramp_speed)/60))
    time.sleep(time_sleep) 
        
    for event in pygame.event.get():
      if event.type == QUIT:sys.exit()
      elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
        END = True

    if END:
      break
    
    vm = float(vmeas.query('READ?')) / vmgain
    print ('vm=',vm)
    print ('vmgain=',vmgain)
    I_leakage = float(v_gateleakage.query('READ?'))*1e3 #leakage current [nA]
    R = vm / i

    print ('R=',R)

    resistance_array = np.append(resistance_array,R)
    applied_gate_array = np.append(applied_gate_array,Vg)
    I_leakage_array = np.append(I_leakage_array,I_leakage)

    current_time = time.time()
    line = [i, vm, R, Vg, T, current_time - last_time, I_leakage]
    stlab.writeline(myfile, line)
    
    myfile.write('\n')
    # stlab.metagen.fromarrays(myfile, Vglist, range(count+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)

    plt.rcParams["figure.figsize"] = [16,9] 
    plt.subplot(2, 1, 1) 
    plt.plot(applied_gate_array,resistance_array, '--r', marker='o')
    plt.title(prefix)
    plt.ylabel('resistance [$\Omega$]')
    plt.xlim(Vgmin,Vgmax)

    
    plt.subplot(2, 1, 2)
    plt.plot(applied_gate_array,I_leakage_array, '--r', marker='o') 
    plt.ylabel('leakage current [nA]') 
    plt.xlabel('gate voltage  [V]')
    plt.xlim(Vgmin,Vgmax)


    plt.pause(0.1)  


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(vgdac,0.,tt=1.) 
ivvi.RampAllZero(tt=1.)
vmeas.close()
ivvi.close()


myfile.close()
