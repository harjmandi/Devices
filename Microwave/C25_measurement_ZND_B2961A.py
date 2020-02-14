''' This program uses R&S ZND to detect the resonace of a microwave cavity and B2961A to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).



	Hardware to be used:
		- R&S ZND VNA
		- Keysight B2961A: For gating
		- Rigol: to power up the room-T amplifier (otional)



	Before runnign the programm:
		- Make sure that room temperature amplifier is well wired: mounted on port 2 of the ZND and it is powered up with 15 V with Rigol

	Wiring:
		-	For the reflection measurements with the directional-coupler inside the fridge: Out put of the ZND (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
			eventually connected to the Port 2 on ZND (through the circulator and low-T amplifier) and "input" port to the resonator.

'''


import os
import numpy as np
import time
import stlab
import stlabutils
from stlab.devices.RS_ZND import RS_ZND
from gate_pattern import gate_pattern
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import pygame, sys
from pygame.locals import *
from matplotlib import cm
from array import *
from stlab.devices.Keysight_B2901A import Keysight_B2901A


###############################################################################################
''' Definitions'''

#definitions

prefix = 'C25-LR_GateCavity_'
time_step = 1 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 1000 # the safe spead for ramping the gate voltage [mV/s]
target_gate = 10 # !!! becareful above +- 30V; normally it reaches the current limit of S1h (monitor the applied voltage using a separate Keithley).
shift_voltage= 0 #in the case the intended gate pattern in not symmetrical around 0.
gate_points = 21
safe_gate_current = 2500 # [nA], safe current leakage limit, above this limit S1h unit gives an error. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!

start_freq = 5.8  # start grequency [GHz]
stop_freq = 6.3 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 2001 # frequency sweep points
SweepTime = 1 # frequency sweep time [s]
frequency = np.linspace (start_freq,stop_freq,freq_points)
power = -10 #sweep power [dB] range: -45 to 3 dB
measure = 'OnePort' # 'OnePort' or 'TwoPort'


# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False
monitor_ratio = 5 #shows 1 out of "monitor_ratio" spectrums
temp = 3.5 # read it manually
adjust_phase = False

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
gate_dev.SetOutputOn()
gate_dev.SetComplianceCurrent(safe_gate_current)


# initializing the ZND
ZND = RS_ZND('TCPIP::192.168.1.149::INSTR', reset=False)

#############################################################
''' measurements '''
# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='single', data_points=gate_points, shift_voltage= shift_voltage )

# modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

ramp_time = np.abs(np.floor(shift_voltage/ramp_spead))
gate_dev.RampVoltage(pattern['ramp_pattern'][0],tt=10*ramp_time, steps = 100)


gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
ramp_time = np.abs(np.floor(gate_voltage_step/ramp_spead))

S21dB = np.array([],[])
S21Ph = np.array([],[])
gate = np.array([])
Leakage_current = np.array([])


for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage
	gate_dev.RampVoltage(gate_voltage,tt=ramp_time, steps = 5)

	leakage_current = float(gate_dev.GetCurrent()) # in the units of [A]
	Leakage_current = np.append(Leakage_current,leakage_current)

	if np.abs(leakage_current) > safe_gate_current:
		GATE_LEAKAGE = True
		print ('gate current', leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
		print ('dielectric resitance is only', oxide_resistance, 'MOhms.')
		print ('reseting the gate voltage')
		dev.RampVoltage(DAC,0,tt=ramp_time)
		break
	print ('\n\n------------------------')


	time.sleep(time_step)

	data = ZND.MeasureScreen_pd()
	if measure == 'OnePort':
		amp_data = np.array(data['S11dB (dB)'])
		phase_data = np.array(data['S11Ph (rad)'])

	elif measure == 'TwoPort':
		amp_data = np.array(data['S21dB (dB)'])
		phase_data = np.array(data['S21Ph (rad)'])

	if count == 0:

		S_amp = amp_data
		S_phase = phase_data


		if adjust_phase:
			plt.plot(data['Frequency (Hz)'],phase_data)
			plt.show()

			Min = float(input('please enter min frequecy range for fitting the phase [GHz]:'))
			Max = float(input('please enter max frequecy range for fitting the phase [GHz]:'))

			index_1 = (np.abs(data['Frequency (Hz)'] - 1e9*Min)).argmin()
			index_2 = (np.abs(data['Frequency (Hz)'] - 1e9*Max)).argmin()

			z = np.polyfit(data['Frequency (Hz)'][index_1:index_2], (phase_data[index_1:index_2]), 1)
			adjusted_phase = (phase_data-z[0]*data['Frequency (Hz)'])*180/np.pi
			adjusted_phase -= np.amin(adjusted_phase)
		else:
			adjusted_phase = phase_data

	else:

		S_amp = np.array(np.vstack((S_amp,amp_data)))
		S_phase = np.array(np.vstack((S_phase,adjusted_phase)))



		plt.rcParams["figure.figsize"] = [16,9]

		if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
			plt.subplot(4, 1, 1)
			plt.plot(data['Frequency (Hz)'],amp_data)
			plt.ylabel('S11dB (dB)')
			plt.text(10, .25,['Power: ', ZND.GetPower() , 'dB'], fontdict=font)
			# plt.xlim(np.minimum(data['Frequency (Hz)']),np.maximum(data['Frequency (Hz)']))

			plt.subplot(4, 1, 2)
			plt.plot(data['Frequency (Hz)'],adjusted_phase*180/np.pi)
			plt.ylabel('Phase (°)')
			# plt.xlim(np.minimum(data['Frequency (Hz)']),np.maximum(data['Frequency (Hz)']))


		plt.subplot(4, 1, 3)
		plt.contourf(data['Frequency (Hz)'],pattern['ramp_pattern'][0:count+1],S_amp)
		plt.ylabel('$V_g$ (V)')
		plt.title('S11dB (dB)')


		plt.subplot(4, 1, 4)
		plt.contourf(data['Frequency (Hz)'],pattern['ramp_pattern'][0:count+1],S_phase*180/np.pi)
		plt.ylabel('$V_g$ (V)')
		plt.xlabel('Frequency (Hz)')
		plt.title('Phase (°)')


	plt.pause(0.1)


	if save_data:

		# temp = tempdev.GetTemperature()
		data['Power (dBm)'] = ZND.GetPower()
		data['Gate Voltage (V)'] = gate_voltage
		data['Leakage Current (A)'] = leakage_current
		data['Temperature (K)'] = temp

		if count==0:
			Data = stlab.newfile(prefix,'_',data.keys(),autoindex = True)
		stlab.savedict(Data, data)

		# stlab.metagen.fromarrays(Data,data['Frequency (Hz)'],powers[0:i+1],xtitle='Frequency (Hz)', ytitle='Power (dB)',colnames=data.keys())


		# stlab.writeline(Data,data)

		# stlab.writeline(Gate_Data,[gate_voltage, leakage_current])


	for event in pygame.event.get(): # stopping if 's' pressed
		if event.type == QUIT: sys.exit()

		if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
			STOP = True

	if STOP:
		break

gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage


print('FINISHED')

#############################################################
''' output '''

if save_data:

	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
	Data.close()
	plt.close()


	plt.plot(pattern['ramp_pattern'],Leakage_current)
	plt.ylabel('leakage current (nA)')
	plt.xlabel('gate (V)')
	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix+'leakage_current')














