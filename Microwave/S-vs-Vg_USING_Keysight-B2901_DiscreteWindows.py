''' This program uses KEYSIGHT FieldFox to detect the resonace of a microwave cavity and B2961A to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).
The frequency range is split into several discrete windows (not neighbouring) and high resolution scanning is done inside each window. This script is more usefull when several resonances are initially detected in coarse scanning.



	Hardware to be used:
		- KEYSIGHT FieldFox
		- Keysight B2961A: For gating



	Before runnign the programm:
		- Make sure that room temperature amplifier is well wired: mounted on port 2 of the KEYSIGHT FieldFox and it is powered up with 15 V with Rigol

	Wiring:
		-	For the reflection measurements with the directional-coupler inside the fridge: Out put of the KEYSIGHT FieldFox (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
			eventually connected to the Port 2 on KEYSIGHT FieldFox (through the circulator and low-T amplifier) and "input" port to the resonator.

'''


import os
import numpy as np
import time
import stlab
import stlabutils
from gate_pattern import gate_pattern
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
from stlab.devices.Keysight_B2901A import Keysight_B2901A


###############################################################################################
''' Definitions'''

#definitions
title = 'C26_UL'
path = 'D:/measurement_data_4KDIY/Hadi/C26 2020-03-11 measurements/'
figures_path = path+'All_Results'

time_step = 1#20 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 10 # the safe spead for ramping the gate voltage [mV/s]
target_gate = 30 #
shift_voltage= 0 #in the case the intended gate pattern in not symmetrical around 0.
gate_points = 120
monitor_ratio = 8 #shows 1 out of "monitor_ratio" spectrums
safe_gate_current = 5e-3 # [A], safe current leakage limit, above this limit S1h unit gives an error. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!

Start_Freq = [6, 7.5, 4.6]  # start grequency [GHz]
Stop_Freq = [6.42, 7.93, 5.45] # stop frequency [GHz] maximum 8.5GHZ for ZND

freq_points = 2001 # frequency sweep points
power = 3 #sweep power [dB] range: -45 to 3 dB
measure = 'TwoPort' # 'OnePort' or 'TwoPort'
averaging  = 1



# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False
temp = 3.5 # read it manually

prefix = title+'_GateSweep'

font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }

##########################################################
''' Initializing the devices '''

# Keysight setting
gate_dev = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
gate_dev.SetModeVoltage()
gate_dev.SetComplianceCurrent(safe_gate_current)
gate_dev.SetOutputOn()



# initializing the ZND
VNA = stlab.adi(addr='TCPIP::192.168.1.230::INSTR',reset=False) # this is FieldFox
# VNA.write('INST:SEL "NA"')  #set mode to Network Analyzer
# if measure == 'OnePort':
# 	VNA.SinglePort()
# elif measure == 'TwoPort':
# 	VNA.TwoPort()


VNA.write("SENS:SWE:POIN " + str(freq_points))

if averaging > 1:
	VNA.write('SENS:AVER:COUN %d' % averaging)
	# VNA.write('SENS:AVER ON')
	# VNA.write('SENS:AVER:CLEAR')
VNA.SetPower(power)
VNA.SetIFBW(100.)


#############################################################
''' measurements '''
# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='single', data_points=gate_points, shift_voltage= shift_voltage )

# modulating the gate voltage
ramp_time = np.abs(np.floor(shift_voltage/ramp_spead))
gate_dev.RampVoltage(pattern['ramp_pattern'][0],tt=10*ramp_time, steps = 100)
gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
ramp_time = np.abs(np.floor(gate_voltage_step/ramp_spead))


for i in range(len(Start_Freq)):

	start_freq = Start_Freq [i]
	stop_freq = Stop_Freq [i]
	frequency = np.linspace (start_freq,stop_freq,freq_points)
	VNA.write("SENS:FREQ:START " + str(start_freq*1e9))
	VNA.write("SENS:FREQ:STOP " + str(stop_freq*1e9))


	count = 0 # couter of step numbers
	leakage_current = 0

	S21dB = np.array([],[])
	S21Ph = np.array([],[])
	gate = np.array([])
	Leakage_current = np.array([])

	t_in = time.time()
	for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage


		gate_dev.RampVoltage(gate_voltage,tt=ramp_time, steps = 5)

		leakage_current = float(gate_dev.GetCurrent()) # in the units of [A]
		Leakage_current = np.append(Leakage_current,leakage_current)


		time.sleep(time_step)

		for j in range(averaging):
			data = VNA.MeasureScreen_pd()

		if measure == 'OnePort':
			amp_data = np.array(data['S11dB (dB)'])
			phase_data = np.array(data['S11Ph (rad)'])

		elif measure == 'TwoPort':
			amp_data = np.array(data['S21dB (dB)'])
			phase_data = np.array(data['S21Ph (rad)'])

		if count == 0:

			S_amp = amp_data
			S_phase = phase_data

		else:

			S_amp = np.array(np.vstack((S_amp,amp_data)))
			S_phase = np.array(np.vstack((S_phase,phase_data)))



			plt.rcParams["figure.figsize"] = [16,9]

			if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
				plt.subplot(3, 1, 1)
				plt.plot(data['Frequency (Hz)']*1e-9,amp_data)
				plt.ylabel('S11dB (dB)')
				plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)
				plt.title(title + ' Power: '+ str(power) + ' dBm')

				plt.subplot(3, 1, 2)
				plt.plot(data['Frequency (Hz)']*1e-9,phase_data*180/np.pi)
				plt.ylabel('Phase (°)')
				plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)


			plt.subplot(3, 1, 3)
			plt.contourf(data['Frequency (Hz)']*1e-9,pattern['ramp_pattern'][0:count+1],S_amp)
			plt.ylabel('$V_g$ (V)')
			plt.title('S11dB (dB)', backgroundcolor = 'white')
			plt.xlabel('Frequency (GHz)')


			# plt.subplot(4, 1, 4)
			# plt.contourf(data['Frequency (Hz)']*1e-9,pattern['ramp_pattern'][0:count+1],S_phase*180/np.pi)
			# plt.ylabel('$V_g$ (V)')
			# plt.title('Phase (°)', backgroundcolor = 'white')


		plt.pause(0.1)


		if save_data:

			# temp = tempdev.GetTemperature()
			data['Power (dBm)'] = VNA.GetPower()
			data['Gate Voltage (V)'] = gate_voltage
			data['Leakage Current (A)'] = leakage_current
			data['Temperature (K)'] = temp

			if count==0:
				Data = stlab.newfile(prefix,'_',data.keys(),autoindex = True, mypath= path)
			stlab.savedict(Data, data)


		for event in pygame.event.get(): # stopping if 's' pressed
			if event.type == QUIT: sys.exit()

			if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
				STOP = True

		if STOP:
			break


		t = time.time()
		print('measured gate steps:', count+1)
		time_passed = t - t_in
		time_remain = (time_passed/(count+1))*(len(pattern['ramp_pattern'])-count-1)
		print('ELAPSED TIME (for this frequency window): {:.2f} min'.format(time_passed/60))
		print('REMAINING TIME (for this frequency window): {:.2f} min'.format(time_remain/60))


	gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage


	print('FINISHED')

	#############################################################
	''' output '''

	if save_data:

		plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
		plt.savefig(figures_path+'\\'+str(i)+'_'+str(start_freq)+'GHz.jpg')

		Data.close()
		plt.close()


		plt.plot(pattern['ramp_pattern'],Leakage_current)
		plt.ylabel('leakage current (nA)')
		plt.xlabel('gate (V)')
		plt.savefig(os.path.dirname(Data.name)+'\\'+prefix+'leakage_current')






















