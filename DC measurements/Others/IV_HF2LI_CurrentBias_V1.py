''' This program is for IV measurement (I bias) using a lock-in amplifier. Keysight_B2901A unit is connected to the HF2LI (add port) to provide 
an offset Voltage (i.e. bias current passing throught a large resistor).
IVVI S1h gates the graphene and the leakage current is measured with the Keithley 

'''



import stlab
import zhinst.utils
import stlabutils
from stlab.devices.IVVI import IVVI_DAC
from stlab.devices.TritonWrapper import TritonWrapper
from my_poll_v2 import R_measure as R_measure

import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
import os
import math
from stlab.devices.Keysight_B2901A import Keysight_B2901A




''' input ''' 
prefix = 'F17_IV_e6_0102_IBias_2probe'

i_BiasMax = 95e-9 #8e-9 # Maximum bias current [A]
i_BiasMin = -i_BiasMax # Minimum bias current [A]
delta_i_bias = 5e-9 # Delta bias current

i_oss = 1e-9# 1e-9 # Oscilation amplitude [A]
R_bias = 10e6 #Bias resistance, to be set on the sample simulator

Vgmax = 60 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 30 # Gate voltage steps [V]
gate_ramp_speed = 0.3 # Gate ramp speed [V/s], proposed: 0.3
time_sleep = 10 #sleep time to stablize the gate [s], proposed: 1

# DACs
vgdac = 1 #DAC number for gate voltage

# gains
vggain = 45. #V/V gain for the applied gate, set on S1h

# Lock in parameters
in_range = 5e-3 # must be larger than 1mV
out_range = 100e-3 # possible ranges: 10e-3, 100e-3, 1, 10 
diff = True 
ac = False
calibration_factor = 1.45

''' Initialize '''  
pygame.init()
pygame.display.set_mode((100,100))

## Temperature readout
mytriton = TritonWrapper()
T = mytriton.GetTemperature(8)

print('### Measure T 10 times ###')

try:
	T = mytriton.GetTemperature(8)
except:
	T = -1

Tini = T*1000.

## IVVI
ivvi = IVVI_DAC(addr='COM5', verb=True)
# ivvi.RampAllZero(tt=10.)

## Keithley
v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.162::INSTR') #for measuring the leakage current

## HF2LI
measure_amplitude = i_oss*R_bias #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.5

apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session('dev352', apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)


# Keysight setting
Keysight = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
Keysight.SetModeVoltage()
Keysight.SetOutputOn()


## Output setting
idstring = 'bias_current{:.0f}nA_at{:.2f}mK'.format(i_BiasMax*1e9,Tini).replace('.','p')
colnames = ['Iset (A)', 'Vmeas (V)', 'Rmeas (Ohm)', 'Vgate (V)', 'Leakage Current (A)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
last_time = time.time()

## Calculation
Vglist = np.linspace(Vgmax, Vgmin, (Vgmax-Vgmin)/deltaVg+1)
iBiaslist = np.linspace(i_BiasMax, i_BiasMin, (i_BiasMax-i_BiasMin)/delta_i_bias+1)



Vg_ini = Vglist[0]
print('############# Initialize back-gate to',Vg_ini,'V #############')
ivvi.RampVoltage(vgdac,Vg_ini/vggain*1000.,tt=Vg_ini/gate_ramp_speed) ##ramping to the 
print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(5*time_sleep,Vg_ini))
time.sleep(5*time_sleep) 

myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True)
END = False
total_count = Vglist.shape[0]

resistance_array = np.array([])
applied_gate_array = np.array([])
I_leakage_array = np.array([])
V_array = np.array([])



plt.rcParams["figure.figsize"] = [16,9] 
plt.xlabel('current [nA]')
plt.ylabel('Voltage [mV]') 
palette = plt.get_cmap('Set1') # create a color palette

for count,Vg in enumerate(Vglist):
	if (i_BiasMax+i_oss)*R_bias > out_range: 
		input ('The combination of the Bias and Oscilation currents with the bias resistance exceeds the output range; press ENTER to exit.')
		break

	ivvi.RampVoltage(vgdac,Vg/vggain*1000.,tt=deltaVg/gate_ramp_speed, steps = 10) ##ramping this voltage in 20seconds
	print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep, Vg))
	time.sleep(time_sleep) 
		
	
	for event in pygame.event.get():
	  if event.type == QUIT:sys.exit()
	  elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
	  		END = True

	if END:
	  break

	I_leakage = float(v_gateleakage.query('READ?'))*1e3 #leakage current [nA]

	V_array = np.array([])
	resistance_array = np.array([]) 
	I_leakage_array = np.array([])

	for i in iBiaslist:

		Keysight.RampVoltage(i*R_bias,tt=0.5, steps = 3)
		measured = R_measure('dev352',
			offset = 0,
			amplitude= measure_amplitude, 
			out_channel = measure_output_channnel, 
			in_channel = measure_input_channnel, 
			time_constant = demodulation_time_constant, 
			frequency = measure_frequency, 
			poll_length = deamodulation_duration, 
			device=device, 
			daq=daq, 
			out_mixer_channel=out_mixer_channel, 
			bias_resistor=R_bias,
			in_range = in_range, 
			out_range = out_range, 
			diff = False,
			add = True,
			ac = ac,
			calibration_factor = calibration_factor)

		Resistance = measured[0] 
		Voltage = Resistance *i
		
		resistance_array = np.append(resistance_array,Resistance)
		V_array = np.append(V_array,Voltage)
		I_leakage_array = np.append(I_leakage_array,I_leakage)

		current_time = time.time()
		line = [i, Voltage, Resistance, Vg, I_leakage, T, current_time - last_time, I_leakage]
		stlab.writeline(myfile, line)
		
		myfile.write('\n')
		# stlab.metagen.fromarrays(myfile, iBiaslist, range(i+1), xtitle='Iset (A)',ytitle='Index_Voltage ()',colnames=colnames)
		time.sleep(time_sleep/5)
	 
	plt.plot(iBiaslist*1e9,V_array*1e3, 'o', color=palette(count), linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
	plt.legend()
	plt.title(prefix)
	plt.pause(0.1)


plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
ivvi.RampVoltage(vgdac,0.,tt=1.) 
ivvi.RampAllZero(tt=1.)
ivvi.close()
zhinst.utils.disable_everything(daq, device)
v_gateleakage.close()
Keysight.RampVoltage(0.,tt=1.)
Keysight.close()


# saving suppelemntary plots
title = 'Resistance'
caption = ''
stlab.autoplot(myfile,'Iset (A)','Rmeas (Ohm)',title=title,caption=caption)
title = 'Leakage Current'
caption = ''
stlab.autoplot(myfile,'Iset (A)','Leakage Current (A)',title=title,caption=caption)

myfile.close()
