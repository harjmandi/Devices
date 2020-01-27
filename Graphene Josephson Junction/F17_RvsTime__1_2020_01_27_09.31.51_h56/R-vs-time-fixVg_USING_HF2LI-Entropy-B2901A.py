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
import zhinst.utils

import time
from my_poll import R_measure as R_measure
import stlab
import stlabutils
import os
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math
from stlab.devices.He7Temperature import He7Temperature


#############################################################
''' Definitions'''

# IO
prefix = 'F17_RvsTime_'
sample_name = 'h56'
do_plot = True
save_data =True


# Gate settings 
gate = 0 # Choose 0 not to apply any gate
time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1500 # the safe speed for ramping the gate voltage [mV/s]


# Temperature settings
delta_t = 1 # measurement every 60s

# HF2LI settings
bias_resistor = 1e6


##########################################################
''' Initializing the devices '''

# initial configuration of the Lock-in
apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session('dev352', apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)

measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.1
calibration_factor = 1.45 # to compensate the shift in resistance measurement


## Temperature readout
tempdev = He7Temperature(addr='145.94.39.138',verb=False)

## Applying gate
leakage_current = 0

if gate != 0:
	from stlab.devices.Keysight_B2901A import Keysight_B2901A
	B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
	B2901A.SetModeVoltage()
	B2901A.SetOutputOn()
	B2901A.SetComplianceCurrent(safe_gate_current)
	B2901A.RampVoltage(gate,tt=gate/0.5, steps = 20)
	leakage_current = float(B2901A.GetCurrent())

# IO settings
pygame.init()
pygame.display.set_mode((100,100))

#############################################################
''' MEASUREMENT'''

if save_data:
	colnames = ['time (s)','temperature (K)', 'gate voltage (V)','leakage current (A)','resistance (ohm)', 'phase ()', 'demodulation duration (s)']
	my_file= stlab.newfile(prefix+'_',sample_name,autoindex=True,colnames=colnames)



END = False
INI_time = time.time()
t0 = INI_time
T0 = 300

TIME = np.empty(shape=(0))
TEMPERATURE = np.empty(shape=(0))
RESISTANCE = np.empty(shape=(0))


while (not END):

	t =  time.time()-INI_time
	# try: 
	# 		T = tempdev.GetTemperature()
	# except: 
	# 	T = -1
	# print ('Temp = ', T)
	T = -1



	measured = R_measure(device_id = 'dev352', 
		amplitude=measure_amplitude,
		out_channel = measure_output_channnel,
		in_channel = measure_input_channnel,
		time_constant = demodulation_time_constant,
		frequency = measure_frequency,
		poll_length = deamodulation_duration,
		device=device, daq=daq,
		out_mixer_channel=out_mixer_channel,
		bias_resistor=bias_resistor)

	measured[0]*=(np.cos(math.radians(measured[1]))*calibration_factor*1000) 

	line = [t,T, gate, leakage_current] + measured

	if save_data:
		stlab.writeline(my_file,line)

	# TEMPERATURE = np.append(TEMPERATURE,T)
	RESISTANCE = np.append(RESISTANCE,measured[0])
	TIME = np.append(TIME,t)

	plt.rcParams["figure.figsize"] = [16,9]


	plt.subplot(2, 1, 1)
	plt.plot(TIME,RESISTANCE, '--b',marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)

	plt.ylabel('Resistance ($\Omega$)')
	plt.xlim(np.min(TIME),np.max(TIME))
	plt.title(prefix+ sample_name)


	plt.subplot(2, 1, 2)
	# plt.plot(TIME/60,TEMPERATURE, '--b', marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)
	# plt.ylabel('Temperature (K)')
	# plt.yscale ('log')
	# plt.xscale ('log')
	# plt.xlabel('Time (min)')

	plt.plot(TIME[:-1], np.diff(RESISTANCE)/np.diff(TIME), '--b', marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)
	plt.xlabel('Temperature (K)')
	plt.xlim(np.min(TIME),np.max(TIME))

	plt.ylabel('$\Delta$R/$\Delta$T ($\Omega/K$)')

	plt.pause(0.1)
	T0 = T

		
	while (time.time()-t0 < delta_t) and (not END):

		for event in pygame.event.get():
			if event.type == QUIT: sys.exit()
			elif event.type == KEYDOWN and event.dict['key'] == 101:
				END = True
				print ('END command detected ...')

		

	t0 = time.time()


print('MEASUREMENT FINISHED')

zhinst.utils.disable_everything(daq, device)

if gate !=0:
	B2901A.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage


#######################################################################
''' saving the data '''


if save_data:

	# saving the metafile
	plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
	my_file.close()



