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
from my_poll_v2 import R_measure as R_measure
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
prefix = 'F18_e6_RvsT_'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F18 2020-02-11 measurements/'

do_plot = True
save_data =True


# Gate settings 
gate = 0 # Choose 0 not to apply any gate
time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1500 # the safe speed for ramping the gate voltage [mV/s]

# Temperature settings
measure_pattern_T = np.array([300, 150, 50, 10, 4]) # Different temperature ranges to set different measurement temperature steps

measure_pattern_dT = np.array([30, 10, 5, 1, 0.1]) # Temperature steps to run a resistance measurements
# measure_pattern_dT = np.array([0.1, 0.1, 1, 1, 0.1]) # Temperature steps to run a resistance measurements

measure_pattern_dt = np.array([5*60, 2*60, 30, 15, 5]) # Time span between two subsequent temperature readings
# measure_pattern_dt = np.array([10, 10, 60, 10, 1]) # Time span between two subsequent temperature readings

# HF2LI settings
bias_resistor = 1e8


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
measure_frequency = 2437 #[Hz]
demodulation_time_constant = 0.45
deamodulation_duration = 1

calibration_factor = 1 # 1.45 recommended  with bias resistance of 1M and demodulation_time_constant = 0.1 # to compensate the shift in resistance measurement
shift = 400 


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
	my_file= stlab.newfile(prefix,'_',autoindex=True,colnames=colnames, mypath= path)



END = False
INI_time = time.time()
t0 = INI_time
T0 = 300

TIME = np.empty(shape=(0))
TEMPERATURE = np.empty(shape=(0))
RESISTANCE = np.empty(shape=(0))


while (not END):

	t =  time.time()-INI_time
	
	try: 
		T = tempdev.GetTemperature()
	except: 
		pass

	print ('Temp = ', T)

	ind = np.where(measure_pattern_T >= T)
	
	if np.abs(T0 - T) > measure_pattern_dT[ind[0][-1]]:
		print ('MEASUREING ...')

		measured = R_measure(device_id = 'dev352', 
		amplitude = measure_amplitude, 
		out_channel = measure_output_channnel, 
		in_channel = measure_input_channnel, 
		time_constant = demodulation_time_constant, 
		frequency = measure_frequency, 
		poll_length = deamodulation_duration, 
		device = device, 
		daq = daq, 
		out_mixer_channel = out_mixer_channel, 
		bias_resistor = bias_resistor, 
		in_range = 4e-3, 
		out_range = 100e-3, 
		diff = False, 
		calibration_factor = 1, 
		add = False, 
		offset = 0, 
		ac = False)

		measured[0] = calibration_factor * measured[0] + shift

		print('resistance =', measured[0])

		line = [t,T, gate, leakage_current] + measured

		if save_data:
			stlab.writeline(my_file,line)

		TEMPERATURE = np.append(TEMPERATURE,T)
		RESISTANCE = np.append(RESISTANCE,measured[0])
		# TIME = np.append(TIME,t)

		plt.rcParams["figure.figsize"] = [16,9]


		plt.subplot(2, 1, 1)
		plt.plot(TEMPERATURE,RESISTANCE, '--b',marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)

		plt.ylabel('Resistance ($\Omega$)')
		plt.xlim(np.min(TEMPERATURE),np.max(TEMPERATURE))
		plt.title(prefix)


		plt.subplot(2, 1, 2)
		# plt.plot(TIME/60,TEMPERATURE, '--b', marker='.',markersize = 1.5, linewidth=0.5, alpha=0.9)
		# plt.ylabel('Temperature (K)')
		# plt.yscale ('log')
		# plt.xscale ('log')
		# plt.xlabel('Time (min)')

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

zhinst.utils.disable_everything(daq, device)

if gate !=0:
	B2901A.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage


#######################################################################
''' saving the data '''


if save_data:

	# saving the metafile
	plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
	my_file.close()



