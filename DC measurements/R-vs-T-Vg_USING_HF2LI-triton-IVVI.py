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
import stlabutils
from stlab.devices.IVVI import IVVI_DAC
from stlab.devices.TritonWrapper import TritonWrapper
import os
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math


#############################################################
''' Definitions'''

# definitions
tempdev = 300
prefix = 'F15_calibration'
sample_name = '2probe'
device_id = 'dev352'
time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1500 # the safe speed for ramping the gate voltage [mV/s]
target_gate = 50
shift_voltage= 10 #in the case the intended gate pattern in not symmetrical around 0.
gate_points = 200
safe_gate_current = 2.5e-6 # [A], safe current leakage limit. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!
time_span = 60 # time span between two subsequent temperature readings
low_temp = 0.14 # stop the measurement when temperature falls below stop_temp
hight_temp = 50 # start the measurement when temperature falls below start_temp

# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.1
calibration_factor = 1.45 # to compensate the shift in resistance measurement

bias_resistor = 1e6

# IVVI settings
s1h_gain = 15 # [V/V] manual gain set on S1h module 
DAC = 1 # DAC linked to the S1h


# output setting
do_plot = True
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


## Temperature readout
mytriton = TritonWrapper()


# resetting the IVVI
dev = IVVI_DAC('COM5') # IVVI
dev.RampAllZero()

# initializing the Keithley for gate current measurement
vmeasure = stlab.adi('TCPIP::192.168.1.161::INSTR',read_termination='\n') # with Keithley DMM6500
# vmeasure=stlab.adi("ASRL1::INSTR") #with Keithley 2000

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

idstring = sample_name
if save_data:
	colnames = ['step ()','gate voltage (V)','leakage current (nA)','Resistance (k ohm)','phase ()', 'demodulation duration (s)', 'temperature (K)', 'time (s)']
	my_file_2= stlab.newfile(prefix+'_',idstring,autoindex=True,colnames=colnames)



gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
ramp_time = np.abs(np.floor(shift_voltage/ramp_speed))

END = False
INI_time = time.time()
TEMPERATURE = np.empty(shape=(0))
RESISTANCE = np.empty(shape=(0))



while (not END) and (low_temp <= mytriton.GetTemperature(8) <= high_temp):


	plt_Vg=np.array([])
	plt_resistance=np.array([])
	plt_leak_curr=np.array([])

	dev.RampVoltage(DAC,1000*shift_voltage/s1h_gain,tt=ramp_time, steps = 20) # the factor 1000 is applied as the unit reads in mV.

	start_T = mytriton.GetTemperature(8)
	
	for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage

		time = time.time() - INI_time
			
		dev.RampVoltage(DAC,1000*gate_voltage/s1h_gain,tt=ramp_time, steps = 5) # the factor 1000 is applied as the unit reads in mV.
		leakage_current = 1e9*gate_leakage_v_I_conversion*float(vmeasure.query('READ?')) # in the units of [nA]

		print ('\n\n------------------------')

		if np.abs(leakage_current) > safe_gate_current:
			GATE_LEAKAGE = True
			print ('gate current', 1e9*leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
			print ('reseting the gate voltage')
			dev.RampVoltage(DAC,0,tt=ramp_time)        

			break

		print('GATE: {:6.4f}'.format(gate_voltage), 'V')


		measured = R_measure(device_id, amplitude=measure_amplitude,
			out_channel = measure_output_channnel,
			in_channel = measure_input_channnel,
			time_constant = demodulation_time_constant,
			frequency = measure_frequency,
			poll_length = deamodulation_duration,
			device=device, daq=daq,
			out_mixer_channel=out_mixer_channel,
			bias_resistor=bias_resistor)

		measured[0]*=(np.cos(math.radians(measured[1])*calibration_factor) 

		line = [count,gate_voltage, leakage_current] + measured + mytriton.GetTemperature(8) + time
		if save_data:
			stlab.writeline(my_file_2,line)

		plt_Vg = np.append(plt_Vg,gate_voltage)
		plt_resistance = np.append(plt_resistance,measured[0])
		plt_leak_curr = np.append(plt_leak_curr,leakage_current)

		plt.rcParams["figure.figsize"] = [16,9]


		if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
			plt.subplot(3, 1, 1)
			plt.plot(plt_Vg,plt_resistance, '--r',marker='o')

			plt.ylabel('Resistance (k$\Omega$)')
			plt.title("Resitance = %4.2f k$\Omega$" %measured[0])


			plt.subplot(3, 1, 2)
			plt.plot(plt_Vg,1e9*plt_leak_curr, '--r', marker='o')
			plt.ylabel('Leakage Current (nA)')
			plt.xlabel('Gate Voltage (V)')
			plt.title("Leackage Current = %4.2f nA" %(1e9*leakage_current))

		for event in pygame.event.get():
			if event.type == QUIT:sys.exit()
			elif event.type == KEYDOWN and event.dict['key'] == 101:
				END = True

		if END:
			break

	plt_resistance = [plt_resistance for _,plt_resistance in sorted(zip(plt_Vg,plt_resistance))]
	GATE = sorted(plt_Vg)
	stop_T = mytriton.GetTemperature(8)
	temp = (start_T+stop_T)/2

	RESISTANCE = np.array(np.vstack((RESISTANCE,plt_resistance)))
	TEMPERATURE = np.array(np.append(TEMPERATURE,temp))

				
	plt.subplot(3, 1, 3)
	plt.contourf(GATE,TEMPERATURE,RESISTANCE)
	plt.ylabel('temperature (K)')
	plt.xlabel('gate voltage (V)')
	plt.title('S11dB (dB)', bbox=dict(facecolor='white', alpha=1))
	

	time.sleep(time_span)
	



print('MEASUREMENT FINISHED')

gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage
zhinst.utils.disable_everything(daq, device)
dev.SetOutputOff()

#######################################################################
''' saving the data '''


if save_data:


	# saving the metafile
	plt.savefig(os.path.dirname(my_file_2.name)+'\\'+prefix)
	my_file_2.close()

	# saving extra plots
	
	title = 'Temperature'
	caption = ''
	stlab.autoplot(my_file_2,'time (s)','temperature (K)',title=title,caption=caption)






