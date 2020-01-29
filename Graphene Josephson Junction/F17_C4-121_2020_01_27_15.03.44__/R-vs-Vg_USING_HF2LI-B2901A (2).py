''' This program uses KEYSIGHT B2901A to apply a gate voltage and HF2LI lock-in amplifier to measure the resistance of the sample



	Hardware to be used:
		- SMU B2901A: For gating
		- A bias resistance of 1M: As voltage to current converter for lock-in out put.
			Note that there is always errors in reading the resitance of the device; the error is around -33% depending on the gain on S4c (see the excel file "Calibrate S4c gain.xlsx").

		- HF2LI: to measure the resistance of graphene device




'''
import numpy as np
import zhinst.utils

from gate_pattern import gate_pattern

import time
from my_poll import R_measure as R_measure
import stlab
import os
from stlab.devices.Keysight_B2901A import Keysight_B2901A
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math


#############################################################
''' Definitions'''

# definitions
tempdev = -1
prefix = 'F17_C4-12'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F17 2020-01-22 measurements/'

device_id = 'dev352'
time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1500 # the safe speed for ramping the gate voltage [mV/s]
target_gate = 50
shift_voltage= 0 #in the case the intended gate pattern in not symmetrical around 0.
gate_points = 200
safe_gate_current = 2.5e-6 # [A], safe current leakage limit. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!

# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.3

bias_resistor = 1e7
calibration_factor = 1.45 # to compensate the shift in resistance measurement


# output setting
do_plot = True
watch_gate_leakage = True # monitors the gate leakage and stops above the safe leakage limit
save_data =True

pygame.init()
pygame.display.set_mode((100,100))

##########################################################
''' Initializing the devices '''

# initial configuration of the Lock-in
apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session(device_id, apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)


# Keysight setting
gate_dev = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
gate_dev.SetModeVoltage()
gate_dev.SetOutputOn()
gate_dev.SetComplianceCurrent(safe_gate_current)


#############################################################
''' MEASUREMENT'''

# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='double', data_points=gate_points, shift_voltage= shift_voltage )


# Resistance measurement while modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

if save_data:
	colnames = ['step ()','gate voltage (V)','leakage current (nA)','Resistance (k ohm)','phase ()', 'demodulation duration (s)']
	my_file_2= stlab.newfile(prefix,'_',autoindex=True,colnames=colnames)

ramp_time = np.abs(np.floor(shift_voltage/ramp_speed))
gate_dev.RampVoltage(shift_voltage,tt=10*ramp_time, steps = 100)

gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
# ramp_time = np.abs(np.floor(gate_voltage_step/ramp_speed))
ramp_time = 0.5
plt_Vg=np.array([])
plt_resistance=np.array([])
plt_leak_curr=np.array([])


END = False

for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage

	for event in pygame.event.get():
		if event.type == QUIT:sys.exit()
		elif event.type == KEYDOWN and event.dict['key'] == 101:
			END = True

	if END:
		break

	gate_dev.RampVoltage(gate_voltage,tt=ramp_time, steps = 5)

	leakage_current = float(gate_dev.GetCurrent()) # in the units of [A]

	print ('\n\n------------------------')


	if watch_gate_leakage:
		if np.abs(leakage_current) > safe_gate_current:
			GATE_LEAKAGE = True
			print ('gate current', 1e9*leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
			print ('reseting the gate voltage')
			gate_dev.RampVoltage(0,tt=ramp_time, steps = 10)
			break

	print('GATE: {:6.4f}'.format(gate_voltage), 'V')

	# time.sleep(time_step)

	measured = R_measure(device_id, amplitude=measure_amplitude,
		out_channel = measure_output_channnel,
		in_channel = measure_input_channnel,
		time_constant = demodulation_time_constant,
		frequency = measure_frequency,
		poll_length = deamodulation_duration,
		device=device, daq=daq,
		out_mixer_channel=out_mixer_channel,
		bias_resistor=bias_resistor)

	measured[0]*=(np.cos(math.radians(measured[1]))*calibration_factor)

	line = [count,gate_voltage, leakage_current] + measured

	if save_data:
		stlab.writeline(my_file_2,line, mypath= path)



	print('LEAKAGE CURRENT: {:6.4f}'.format(1e9*leakage_current), 'nA')
	print('RESISTANCE: {:6.2f}'.format(measured[0]), 'kOhms')
	print('PHASE {:4.2f}'.format(measured[1]))

	plt_Vg = np.append(plt_Vg,gate_voltage)
	plt_resistance = np.append(plt_resistance,measured[0])
	plt_leak_curr = np.append(plt_leak_curr,leakage_current)

	plt.rcParams["figure.figsize"] = [16,9]
	plt.subplot(2, 1, 1)
	plt.plot(plt_Vg,plt_resistance, '--r',marker='o')

	plt.ylabel('Resistance (k$\Omega$)')
	plt.title("Resitance = %4.2f k$\Omega$" %measured[0])


	plt.subplot(2, 1, 2)
	plt.plot(plt_Vg,1e9*plt_leak_curr, '--r', marker='o')
	plt.ylabel('Leakage Current (nA)')
	plt.xlabel('Gate Voltage (V)')
	plt.title("Resistance = %4.2f k$\Omega$, Leackage Current = %4.2f nA" %(measured[0], 1e9*leakage_current))

	plt.pause(0.1)


print('RAMPING FINISHED')

gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage


zhinst.utils.disable_everything(daq, device)
gate_dev.SetOutputOff()

print('FINISHED')


#######################################################################
''' saving the data '''

if save_data:


	# saving the metafile
	plt.savefig(os.path.dirname(my_file_2.name)+'\\'+prefix)
	my_file_2.close()

	parameters = ['target gate (V)',
		'time step (s)',
		'gate points ()',
		'measure amplitude (V)',
		'measure frequency (Hz)',
		'bias resistor (Ohm)',
		'deamodulation duration (s)',
		'demodulation time constant (s)',
		'temperature (K)']

	T = tempdev

	parameters_line =[target_gate,
		time_step,
		gate_points,
		measure_amplitude,
		measure_frequency,
		bias_resistor,
		deamodulation_duration,
		demodulation_time_constant,
		T]
	my_file= stlab.newfile(prefix+'_',idstring + '_metadata',autoindex=False,colnames=parameters,usefolder=False,mypath = os.path.dirname(my_file_2.name),usedate=False)
	stlab.writeline(my_file,parameters_line, mypath= path)

	# saving the plots
	title = 'Resistance'
	caption = ''
	stlab.autoplot(my_file_2,'gate voltage (V)','Resistance (k ohm)',title=title,caption=caption)
	title = 'Phase'
	caption = ''
	stlab.autoplot(my_file_2,'gate voltage (V)','phase ()',title=title,caption=caption)
	title = 'Duration'
	caption = ''
	stlab.autoplot(my_file_2,'gate voltage (V)','demodulation duration (s)',title=title,caption=caption)
	title = 'Leakage Current'
	caption = ''
	stlab.autoplot(my_file_2,'gate voltage (V)','leakage current (nA)',title=title,caption=caption)





