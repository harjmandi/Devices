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
prefix = 'F17_IV_d6_0102_4probe'

ismax = 10e-6 # Maximum current [A]
ismin = -ismax # Maximum current [A]
deltaI = 10e-9  # Current resolution [A]

Vgmax = 0 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 25 # Gate voltage steps [V]
gate_ramp_speed = 0.5 # Gate ramp speed [V/s], proposed: 0.1
time_sleep = 10 #sleep time to stablize the gate [s], proposed: 20

# DACs
vgdac = 1 #DAC number for gate voltage
isdac = 3  #DAC number for current source

# gains
vmgain = 100  #V/V gain for vmeas set on M2m unit
vggain = 45. #V/V gain for the applied gate, set on S1h
isgain = 100e-9  #Full range of the applied current, set on S4c



''' Initialize '''  
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
mytriton = TritonWrapper()
T = mytriton.GetTemperature(8)

print('### Measure T 10 times ###')
try:
    T0 = mytriton.GetTemperature(8)
except:
    T0 = -1
time.sleep(1)
for x in range(9):
    try:
        T = mytriton.GetTemperature(8)
    except:
        T = -1
    T0 += T
Tini = T0/10.*1000.

##Communicate with devices
ivvi = IVVI_DAC(addr='COM5', verb=True)
ivvi.RampAllZero(tt=10.)

vmeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR')


islist1 = np.arange(0, ismax, deltaI)
islist = np.concatenate([islist1[:-1], islist1[::-1], -islist1[1:-1], -islist1[::-1]])

idstring = '_at{:.2f}mK'.format(Tini).replace('.','p')
colnames = ['Iset (A)', 'Vmeas (V)', 'Rmeas (Ohm)', 'Vgate (V)', 'T (mK)', 'Time (s)']
last_time = time.time()

Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
Vg_ini = Vglist[0]
print('############# Initialize back-gate to',Vg_ini,'V #############')
ivvi.RampVoltage(vgdac,Vg_ini/vggain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
print('Wait 1min for back-gate satbility at',Vg_ini,'V')
time.sleep(60.) 

myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)
END = False
total_count = Vglist.shape[0]

plt.rcParams["figure.figsize"] = [16,9] 
plt.xlabel('current [nA]')
plt.ylabel('voltage [V]') 
palette = plt.get_cmap('Set1') # create a color palette



for i,Vg in enumerate(Vglist):
    ivvi.RampVoltage(vgdac,Vg/vggain*1000.,tt=deltaVg/gate_ramp_speed) ##ramping this voltage in 20seconds
    print('Wait 20s for back-gate stability at', Vg,'V')
    print('Time remaining: {:.0f} min'.format((total_count-i)*(time_sleep+deltaVg/gate_ramp_speed)/60))
    time.sleep(time_sleep) 
        
    for event in pygame.event.get():
      if event.type == QUIT:sys.exit()
      elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
        END = True

    if END:
      break

    try:  ##for each voltage sweep it will read the temperature and save in the data file
      T = mytriton.GetTemperature(8)
    except:
      T = -1  
    
    ivvi.RampVoltage(isdac, islist[0] / isgain * 1e3,tt=10.)  #initialize first current value
    
    V = []
    for curr in islist:
      ivvi.SetVoltage(isdac, curr / isgain *1e3)  #Take curr in amps, apply gain and convert to millivolts
      im = curr  #Do not measure current
      vm = float(vmeas.query('READ?')) / vmgain
      V = np.append(V,vm)
      Iset = curr
      R = vm / im
      current_time = time.time()
      line = [Iset, vm, R, Vg, T, current_time - last_time]
      stlab.writeline(myfile, line)
    
    myfile.write('\n')
    stlab.metagen.fromarrays(myfile, islist, range(i+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)
    ivvi.RampVoltage(isdac, 0, tt=10.)

     
    plt.plot(islist*1e9,V, 'o', color=palette(i), linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
    plt.legend()
    plt.title(prefix)
    plt.pause(0.1)  

plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(vgdac,0.,tt=30)
ivvi.RampAllZero(tt=10.)
vmeas.close()
ivvi.close()


myfile.close()
