''' The goal odf this program is to sweep the frequency of the lock-in to estimate the R,L and C paramters of a circuit.



	Hardware to be used:
		- SMU B2901A: For gating
		- A bias resistance: As voltage to current converter for lock-in out put.
		- HF2LI: to measure the resistance of graphene device




'''
import numpy as np
import zhinst.utils

from gate_pattern import gate_pattern

import time
from my_poll_v2 import R_measure as R_measure
import stlab
import os
from stlab.devices.IVVI import IVVI_DAC
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math


#############################################################
''' Definitions'''

# definitions
tempdev = -1
prefix = 'F18_e6-12_FE_2probe'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F18 2020-02-11 measurements/'

time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 500 # the safe speed for ramping the gate voltage [mV/s]
target_gate = 0
shift_voltage= 0 #in the case the intended gate pattern in not symmetrical around 0.
gate_points = 70
safe_gate_current = 2.5e-6 # [A], safe current leakage limit. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!

s1h_gain = 45 # [V/V] manual gain set on S1h module 
DAC = 1 # DAC linked to the S1h


# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
Measure_Frequency = np.linespace(1e3,50e6,50) #[Hz]
demodulation_time_constant = 0.1
deamodulation_duration = 0.2

in_range = 1#100e-3 
out_range = 100e-3 
diff = False 
add = False 
offset = 0 
ac = False



bias_resistor = 1e6

# Calibration parameters; experimentally achieved to adjst the resistance reading 
	# CASE 1: bias resistance of 1M and demodulation_time_constant = 0.1 =>> calibration_factor = 1.45 and shift = 0
	# CASE 2: bias resistance of 10M and demodulation_time_constant = 0.45 =>> calibration_factor = 1 and shift = 400
calibration_factor = 1 # 1.45 recommended  with bias resistance of 1M and demodulation_time_constant = 0.1 # to compensate the shift in resistance measurement
shift = 400 

# output setting
watch_gate_leakage = True # monitors the gate leakage and stops above the safe leakage limit
save_data = True

pygame.init()
pygame.display.set_mode((100,100))

##########################################################
''' Initializing the devices '''

# initial configuration of the Lock-in
apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session('dev352', apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)

# resetting the IVVI
dev = IVVI_DAC('COM4') # IVVI
dev.RampAllZero()

ramp_time = np.abs(np.floor(shift_voltage/ramp_speed))
dev.RampVoltage(DAC,1000*shift_voltage/s1h_gain,tt=ramp_time, steps = 20) # the factor 1000 is applied as the unit reads in mV.


# initializing the Keithley for gate current measurement
if watch_gate_leakage:
	vmeasure = stlab.adi('TCPIP::192.168.1.105::INSTR',read_termination='\n') # with Keithley DMM6500
	vmeasure.write('SENS:VOLT:DC:RANG:AUTO 0')
	vmeasure.write('SENS:VOLT:DC:RANGE 2')
	vmeasure.write(':INIT:CONT 0')
	vmeasure.write('VOLT:NPLC 1')
	vmeasure.write('TRIG:SOUR IMM')
	vmeasure.write(":SYST:AZER:STAT OFF")
	vmeasure.write(":TRIG:COUN 1")
	gate_leakage_v_I_conversion = 1e-6 # conversion factor of the measured voltage on S1h 'Current monitor' to leakage current



#############################################################
''' MEASUREMENT'''

# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='double', data_points=gate_points, shift_voltage= shift_voltage )


# Resistance measurement while modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

if save_data:
	colnames = ['step ()','gate voltage (V)','leakage current (nA)','resistance (ohm)','impedence (ohm)','phase ()', 'demodulation duration (s)', 'Vx (V)', 'Vy (V)']
	my_file_2= stlab.newfile(prefix,'_',autoindex=True,colnames=colnames, mypath= path)

ramp_time = np.abs(np.floor(shift_voltage/ramp_speed))
dev.RampVoltage(DAC,1000*shift_voltage/s1h_gain,tt=ramp_time, steps = 20) # the factor 1000 is applied as the unit reads in mV.

gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
# ramp_time = np.abs(np.floor(gate_voltage_step/ramp_speed))
ramp_time = 0.5
plt_freq=np.array([])
plt_resistance=np.array([])
plt_leak_curr=np.array([])


END = False

for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage

	dev.RampVoltage(DAC,1000*gate_voltage/s1h_gain,tt=ramp_time) # the factor 1000 is applied as the unit reads in mV.


	if watch_gate_leakage:
		leakage_current = 1e9*gate_leakage_v_I_conversion*float(vmeasure.query('READ?')) # in the units of [nA]

		oxide_resistance = 1e-6*gate_voltage/(leakage_current*1e-9)
		if np.abs(leakage_current*1e-9) > safe_gate_current:
			GATE_LEAKAGE = True
			print ('gate current', leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
			print ('dielectric resitance is only', oxide_resistance, 'MOhms.')
			print ('reseting the gate voltage')
			dev.RampVoltage(DAC,0,tt=ramp_time)        
			break

	print ('\n\n------------------------')

	print('GATE: {:6.4f}'.format(gate_voltage), 'V')
			
	time.sleep(time_step)

	for count_freq, measure_frequency in enumerate(Measure_Frequency)
		
		for event in pygame.event.get():
			if event.type == QUIT:sys.exit()
			elif event.type == KEYDOWN and event.dict['key'] == 101:
				END = True

		if END:
			break

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
			in_range = in_range, 
			out_range = out_range, 
			diff = diff, 
			add = add, 
			offset = offset, 
			ac = ac)

		measured[0] = measured[0] + shift
		line = [count,gate_voltage, leakage_current] + measured

		if save_data:
			stlab.writeline(my_file_2,line)


		print('LEAKAGE CURRENT: {:6.4f}'.format(1e9*leakage_current), 'nA')
		print('RESISTANCE: {:6.2f}'.format(measured[0]), 'Ohms')
		print('PHASE {:4.2f}'.format(measured[1]))

		plt_freq = np.append(plt_freq,measure_frequency)
		plt_resistance = np.append(plt_resistance,measured[0])

		plt.rcParams["figure.figsize"] = [16,9]
		# plt.subplot(2, 1, 1)
		plt.plot(plt_Vg,plt_resistance, '--b',marker='.', markersize = 1, linewidth= 0.2)
		plt.ylabel('Resistance ($\Omega$)')
		plt.title(prefix)
		plt.xlabel('Gate Voltage (V)')



		# plt.subplot(2, 1, 2)
		# plt.plot(plt_Vg,plt_leak_curr, '--b', marker='.',markersize = 1, linewidth= 0.2)
		# plt.ylabel('Leakage Current (nA)')
		# plt.xlabel('Gate Voltage (V)')
		# plt.title("Resistance = %4.2f $\Omega$, Leackage Current = %4.2f nA" %(measured[0], leakage_current))

		plt.pause(0.1)


print('RAMPING FINISHED')

dev.RampVoltage(DAC,0,tt=ramp_time) # to safely return back the gate voltage
zhinst.utils.disable_everything(daq, device)
if watch_gate_leakage:
	vmeasure.close()

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
	my_file= stlab.newfile(prefix,'_metadata',autoindex=False,colnames=parameters,usefolder=False,mypath = os.path.dirname(my_file_2.name),usedate=False)
	stlab.writeline(my_file,parameters_line)

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





