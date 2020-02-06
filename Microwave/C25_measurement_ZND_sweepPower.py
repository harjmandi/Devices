''' This program uses R&S ZND to detect the resonace of a microwave cavity and the  IVVI S1H to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot). 



	Hardware to be used: 
		- R&S ZND VNA
		- IVVI DAC (S1h): For gating
		- Keithley 2000 or DMM6500:  to measure the leakacge current
		- He7Temperature: to measure the temperature of the fridge
		- Rigol: to power up the room-T amplifier
	


	Before runnign the programm: 
		- Make sure that in S2d, the appropriate DAC (in cyurrent version, DAC 1) is set to S1h.
		- Set an appropriate gain on the S1h
		- If using DMM6500, switch to SCPI2000
		- Make sure the low-T amplifier is well wired on the Matrix Module: Vg => pin #2, Vd => pin #3, GND => pin #4
		- Make sure that room temperature amplifier is well wired: mounted on port 2 of the ZND and it is powered up with 15 V with Rigol 
		- Choose appropriate gate range (30V, 60V, 90V) and use the corresponding conversion factor as s1h_gain. 

	Wiring: 
		-	For the reflection measurements with the directional-coupler inside the fridge: Out put of the ZND (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
			eventually connected to the Port 2 on ZND (through the circulator and low-T amplifier) and "input" port to the resonator. 
		- Gate connection is via the free pin 3 or 4 on the fridge; connected to the S1h using SMA to BNC and then BNC to Lemo convertions. 
		- Gate leakage monitoring using MCS to BNC cable from "Current monitor" probe on S1h to KEITHLEY.
 
'''


import os
import numpy as np
import time
import stlab
import stlabutils
from stlab.devices.RS_ZND import RS_ZND
from stlab.devices.He7Temperature import He7Temperature
from gate_pattern import gate_pattern
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import pygame, sys
from pygame.locals import *
from stlab.devices.IVVI import IVVI_DAC
from matplotlib import cm
from array import *

font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }


###############################################################################################
''' Definitions'''

#definitions

prefix = 'C25_UL_3p5K'
time_step = 1 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 1000 # the safe spead for ramping the gate voltage [mV/s]
gate = 0 # !!! becareful above +- 30V; normally it reaches the current limit of S1h (monitor the applied voltage using a separate Keithley).

start_freq = 4  # start grequency [GHz]
stop_freq = 8.5 # stop frequency [GHz]
freq_points = 501 # frequency sweep points
SweepTime = 0.5 # frequency sweep time [s]
frequency = np.linspace (start_freq,stop_freq,freq_points)
start_power = -40 #sweep power [dB] range: -45 to 3 dB
end_power = 3
power_points = 200
measure = 'OnePort' # 'OnePort' or 'TwoPort'
# IVVI settings 
s1h_gain = 15 # [V/V] manua l gain set on S1h module 
DAC = 1 # DAC linked to the S1h


# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False
monitor_ratio = 5 #shows 1 out of "monitor_ratio" spectrums 


##########################################################
''' Initializing the devices '''

# resetting the IVVI
dev = IVVI_DAC('COM4') # IVVI
dev.RampAllZero()


# initializing the ZND

ZND = RS_ZND('TCPIP::192.168.1.149::INSTR', reset=True) 
ZND.ClearAll()
if measure == 'OnePort':
	ZND.SinglePort()

elif measure == 'TwoPort':
	ZND.TwoPort()

ZND.SetSweepfrequency(start_freq, stop_freq, freq_points)
ZND.SetIFBW(1e3) #Set IF bandwidth in Hz
ZND.SetSweepTime(SweepTime)
ZND.AutoScale()

# initializing the temperature reading 
tempdev = He7Temperature(addr='192.168.1.249',verb=False)
temp = 0

#############################################################
''' measurements '''
# generating gate pattern
power_pattern = np.linspace(start_power,end_power,power_points)

# modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

ramp_time = np.abs(np.floor(gate/ramp_spead))
dev.RampVoltage(DAC,1000*gate/s1h_gain,tt=ramp_time) # the factor 1000 is applied as the unit reads in mV.

Temp = np.array([])
S_amp = np.array([],[])
S_phase = np.array([],[])

for count,power in enumerate(power_pattern): # ramping up the gate voltage
	
	ZND.SetPower(power)
	
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
		
		S_amp = np.array(np.vstack((S_amp,amp_data)))
		S_phase = np.array(np.vstack((S_phase,adjusted_phase)))



		plt.rcParams["figure.figsize"] = [16,9]
		
		if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
			plt.subplot(4, 1, 1)
			plt.plot(data['Frequency (Hz)'],amp_data)
			plt.ylabel('S11dB (dB)')
			plt.text(10, .25,['Power: ', ZND.GetPower() , 'dB'], fontdict=font)
			plt.xlim(1e9*start_freq,1e9*stop_freq)


			plt.subplot(4, 1, 2)
			
			plt.plot(data['Frequency (Hz)'],adjusted_phase)
			plt.ylabel('Phase (°)')
			plt.xlim(1e9*start_freq,1e9*stop_freq)


		
		plt.subplot(4, 1, 3)
		plt.contourf(data['Frequency (Hz)'],power_pattern[0:count+1],S_amp)
		plt.ylabel('power (dB)')
		plt.title('S11dB (dB)')

		
		plt.subplot(4, 1, 4)
		plt.contourf(data['Frequency (Hz)'],power_pattern[0:count+1],S_phase)
		plt.ylabel('power (dB)')
		plt.xlabel('Frequency (Hz)')
		plt.title('Phase (°)')

	
	plt.pause(0.1)

	if save_data:

		# temp = tempdev.GetTemperature()
		data['Power (dBm)'] = ZND.GetPower()
		data['Gate Voltage (V)'] = gate
		data['Temperature (K)'] = temp
		data['Adjusted Phase (°)'] = adjusted_phase

		if count==0:
			Data = stlab.newfile(prefix,'_',data.keys(),autoindex = True)
		stlab.savedict(Data, data)
		Temp = np.append(Temp,temp)

		# stlab.metagen.fromarrays(Data,data['Frequency (Hz)'],powers[0:i+1],xtitle='Frequency (Hz)', ytitle='Power (dB)',colnames=data.keys())


		# stlab.writeline(Data,data)
		
		# stlab.writeline(Gate_Data,[gate_voltage, leakage_current])

	
	for event in pygame.event.get(): # stopping if 's' pressed
		if event.type == QUIT: sys.exit()
				
		if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
			STOP = True

	if STOP:
		break

dev.RampVoltage(DAC,0,tt=ramp_time) # to safely return back the gate voltage
dev.close()



print('FINISHED')    

#############################################################
''' output '''

if save_data:

	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
	Data.close()
	plt.close()








 




