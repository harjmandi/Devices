''' This program uses KEYSIGHT B2901A to apply a current to the magnetic coil and HF2LI lock-in amplifier to measure the resistance of the sample



	Hardware to be used:
		- A bias resistor as voltage to current converter for lock-in out put. This resistor should be chosen wisely as the measure_amplitude/bias_resistor should stay below the critical current of the superconductor. 
		- HF2LI: to measure the resistance of graphene device
		- KEYSIGHT B2901A to apply the bias current to the magnetic coil. 



'''
import numpy as np
import zhinst.utils

import time
from my_poll import R_measure as R_measure
import stlab
import os
from stlab.devices.Keysight_B2901A import Keysight_B2901A
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math
import sys

#############################################################
''' Definitions'''

# definitions
tempdev = 0.016
prefix = 'F17_h12'
device_id = 'dev352'
time_step = 3 #time step between each current steps, to stablize the magnetic field
ramp_speed = 10 # tRampCurrenthe safe speed for ramping the current voltage [mA/s]
target_B = 100e-3 #[mT] 
current_points = 200

# HF2LI settings
measure_amplitude = 1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.3
bias_resistor = 1e6
in_range = 5e-3
out_range = 1

calibration_factor = 1.45 # to compensate the shift in resistance measurement


# output setting
do_plot = True
save_data =True

pygame.init()
pygame.display.set_mode((100,100))

##########################################################
''' Initializing the devices '''
B_I_conversion = 0.068 #1A = 0.068T
I_max = target_B/B_I_conversion
if target_B > 150e-3:
	print('Target magnetic field exceeds 150mT; Terminating the program ...')
	sys.exit()

# initial configuration of the Lock-in
apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session(device_id, apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)


# Keysight setting
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeCurrent()
B2901A.SetOutputOn()


#############################################################
''' MEASUREMENT'''

# generating current pattern
I_bias_list = np.linspace(0, I_max, current_points)


# Resistance measurement while modulating the gate voltage
count = 0 # couter of step numbers

idstring = 'R_vs_B'
if save_data:
	colnames = ['Step ()','Current (A)', ' Magnetic Field(T)', 'Resistance (k ohm)','phase ()', 'demodulation duration (s)']
	my_file= stlab.newfile(prefix+'_',idstring,autoindex=True,colnames=colnames)

ramp_time = np.abs(np.floor(I_bias_list[1]/(ramp_speed*1000)))

I_array=np.array([])
R_array=np.array([])
B_array=np.array([])


END = False

for count,I in enumerate(I_bias_list): # ramping up the gate voltage

	for event in pygame.event.get():
		if event.type == QUIT:sys.exit()
		elif event.type == KEYDOWN and event.dict['key'] == 101:
			END = True

	if END:
		break

	B2901A.RampCurrent(I,tt=ramp_time, steps = 5)

	B = float(B2901A.GetCurrent())* B_I_conversion# in the units of [T]

	time.sleep(time_step)

	measured = R_measure(device_id, amplitude=measure_amplitude,
		out_channel = measure_output_channnel,
		in_channel = measure_input_channnel,
		time_constant = demodulation_time_constant,
		frequency = measure_frequency,
		poll_length = deamodulation_duration,
		device=device, daq=daq,
		out_mixer_channel=out_mixer_channel,
		bias_resistor=bias_resistor,
		in_range = in_range, 
		out_range = out_range,
		offset =0)

	measured[0]*=(np.cos(math.radians(measured[1]))*calibration_factor*1000) #the my_poll function returns the resistance in kOhms, so the factor 1000 is used to convert the unit to Ohms.

	line = [count,I, B] + measured


	if save_data:
		stlab.writeline(my_file,line)



	I_array = np.append(I_array,I)
	R_array = np.append(R_array,measured[0])
	B_array = np.append(B_array,B)

	plt.rcParams["figure.figsize"] = [16,9]
	plt.plot(B_array*1000,R_array, '--r',marker='.')

	plt.ylabel('Resistance ($\Omega$)')
	plt.xlabel('Magnetic field (mT)')

	plt.title(prefix)

	plt.pause(0.1)



#######################################################################
''' saving the data '''

if save_data:


	# saving the metafile
	plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
	


	# saving the plots
	title = 'Resistance'
	caption = ''
	stlab.autoplot(my_file,'Current (A)','Resistance (k ohm)',title=title,caption=caption)
	title = 'Phase'
	caption = ''
	stlab.autoplot(my_file,'Current (A)','phase ()',title=title,caption=caption)
	title = 'Duration'
	caption = ''
	stlab.autoplot(my_file,'Current (A)','demodulation duration (s)',title=title,caption=caption)
	title = 'Leakage Current'
	caption = ''

	my_file.close()



B2901A.RampCurrent(0,tt=60) # to safely return back the gate voltage
B2901A.SetOutputOff()
zhinst.utils.disable_everything(daq, device)

