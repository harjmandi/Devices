''' This program uses IVVI S1H to apply a gate voltage and HF2LI lock-in amplifier to measure the resistance of the sample



	Hardware to be used: 
		- IVVI DAC (S1h): For gating
		- IVVI DAC (S4c): As voltage to current converter for lock-in out put. Alternatively an external bios resistor can be used for this purpose.
			Note that there is always errors in reading the resitance of the device; the error is around -33% depending on the gain on S4c (see the excel file "Calibrate S4c gain.xlsx").
		
		- HF2LI: to measure the resistance of graphene device
		- Keithley 2000 or DMM6500:  to measure the leakacge current
		- He7Temperature: to measure the temperature of the fridge
	


	Before runnign the programm: 
		- Make sure that in S2d, the appropriate DAC (in cyurrent version, DAC 1) is set to S1h.
		- Make sure that in S2d, the appropriate connection between Dual iso-in (Iso-Amp1) and S4c (E1) is made. 
		- Set an appropriate gain on the S1h


 
'''

import zhinst.utils
import numpy as np
from gate_pattern import gate_pattern
import time
from my_poll import R_measure as R_measure
import stlab
import os
# from stlab.devices.He7Temperature import He7Temperature
from stlab.devices.IVVI import IVVI_DAC
import matplotlib.pyplot as plt
import pygame, sys 
from pygame.locals import *
import math



#############################################################
''' Definitions'''

# definitions
tempdev = 0.014
prefix = 'F10_FE_e6_0204'
sample_name = '2probe'
device_id = 'dev352'
time_step = 0.2 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 1500 # the safe speed for ramping the gate voltage [mV/s]
target_gate = 30
shift_voltage= 0 #in the case the intended gate pattern in not symmetrical around 0. 
gate_points = 100

# IVVI settings
s1h_gain = 30 # [V/V] manual gain set on S1h module 
DAC = 1 # DAC linked to the S1h

# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 77 #[Hz]
demodulation_time_constant = 0.01
deamodulation_duration = 0.3
bias_resistor = 1e6 # when using S4c as a current source 

calibration_factor = 1.45 # to compensate the shift in resistance measurement

# bias_resistor = 10e6 # when using a bias resitor for V/I conversion



# Keithley setting
safe_gate_current = 2500 # [nA], safe current leakage limit, above this limit S1h unit gives an error. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!
# min_oxide_resitance = 5e5 # minimum acceptable oxide restance, without considering leacky oxide.   


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

# resetting the IVVI
dev = IVVI_DAC('COM5') # IVVI
dev.RampAllZero()

# initializing the Keithley for gate current measurement
vmeasure = stlab.adi('TCPIP::192.168.1.162::INSTR',read_termination='\n') # with Keithley DMM6500
# vmeasure=stlab.adi("ASRL1::INSTR") #with Keithley 2000


vmeasure.write('SENS:VOLT:DC:RANG:AUTO 0')
vmeasure.write('SENS:VOLT:DC:RANGE 2')
vmeasure.write(':INIT:CONT 0')
vmeasure.write('VOLT:NPLC 1')
vmeasure.write('TRIG:SOUR IMM')
vmeasure.write(":SYST:AZER:STAT OFF")
vmeasure.write(":TRIG:COUN 1")
gate_leakage_v_I_conversion = 1e-6 # conversion factor of the measured voltage on S1h 'Current monitor' to leakage current

# initializing the temperature reading 
# tempdev = He7Temperature(addr='192.168.1.249',verb=False)






#############################################################
''' MEASUREMENT'''

# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='double', data_points=gate_points, shift_voltage= shift_voltage )


# Resistance measurement while modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

idstring = sample_name
if save_data:
	colnames = ['step ()','gate voltage (V)','leakage current (nA)','Resistance (k ohm)','phase ()', 'demodulation duration (s)']
	my_file_2= stlab.newfile(prefix+'_',idstring,autoindex=True,colnames=colnames)

ramp_time = np.abs(np.floor(shift_voltage/ramp_speed))
dev.RampVoltage(DAC,1000*shift_voltage/s1h_gain,tt=ramp_time, steps = 20) # the factor 1000 is applied as the unit reads in mV.


gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
ramp_time = np.abs(np.floor(gate_voltage_step/ramp_speed))

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

	dev.RampVoltage(DAC,1000*gate_voltage/s1h_gain,tt=ramp_time) # the factor 1000 is applied as the unit reads in mV.

	leakage_current = 1e9*gate_leakage_v_I_conversion*float(vmeasure.query('READ?')) # in the units of [nA]

	print ('\n\n------------------------')
	

	if watch_gate_leakage:
		oxide_resistance = 1e-6*gate_voltage/(leakage_current*1e-9)
		if np.abs(leakage_current) > safe_gate_current:
			GATE_LEAKAGE = True
			print ('gate current', leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
			print ('dielectric resitance is only', oxide_resistance, 'MOhms.')
			print ('reseting the gate voltage')
			dev.RampVoltage(DAC,0,tt=ramp_time)        
			break

	print('GATE: {:6.4f}'.format(gate_voltage), 'V')
			
	time.sleep(time_step)

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
		stlab.writeline(my_file_2,line)
	


	print('LEAKAGE CURRENT: {:6.4f}'.format(leakage_current), 'nA')
	print('RESISTANCE: {:6.2f}'.format(measured[0]), 'kOhms')
	print('PHASE {:4.2f}'.format(measured[1]))

	plt_Vg = np.append(plt_Vg,gate_voltage)
	plt_resistance = np.append(plt_resistance,measured[0])
	plt_leak_curr = np.append(plt_leak_curr,leakage_current)

	plt.rcParams["figure.figsize"] = [12,9]
	plt.subplot(2, 1, 1)
	plt.plot(plt_Vg,plt_resistance, '--r',marker='o')
	
	plt.ylabel('Resistance ($k\Omega$)')
	plt.title("Resistance = %4.2f k$\Omega$" %measured[0])


	plt.subplot(2, 1, 2)
	plt.plot(plt_Vg,plt_leak_curr, '--r', marker='o')
	plt.ylabel('Leakage Current (nA)')
	plt.xlabel('Gate Voltage (V)')
	plt.text(60, .025,['Leackage Current =', leakage_current , 'nA'])
	# plt.title("phase = %4.2f ()" %(measured[1]))

	plt.pause(0.1)


print('RAMPING FINISHED')

dev.RampVoltage(DAC,0,tt=ramp_time) # to safely return back the gate voltage


zhinst.utils.disable_everything(daq, device)
dev.close()

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





