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
		- Gate connection is via the free pin 3 or 4 on the fridge; connected to the S1h using SMA to BNA and then BNC to Lemo convertions. 
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

# IVVI settings 
s1h_gain = 15 # [V/V] manua l gain set on S1h module 
DAC = 1 # DAC linked to the S1h


# output setting
watch_gate_leakage = False # monitors the gate leakage and stops above the safe leakage limit
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

if watch_gate_leakage: 
	# initializing the Keithley for gate current measurement
	
	vmeasure = stlab.adi('TCPIP::192.168.1.105::INSTR',read_termination='\n') # with Keithley DMM6500
	# vmeasure=stlab.adi("ASRL1::INSTR") #with Keithley 2000
	vmeasure.write('SENS:VOLT:DC:RANG:AUTO 0')
	vmeasure.write('SENS:VOLT:DC:RANGE 2')
	vmeasure.write(':INIT:CONT 0')
	vmeasure.write('VOLT:NPLC 1')
	vmeasure.write('TRIG:SOUR IMM')
	vmeasure.write(":SYST:AZER:STAT OFF")
	vmeasure.write(":TRIG:COUN 1")

gate_leakage_v_I_conversion = 1e-6 # conversion factor of the measured voltage on S1h 'Current monitor' to leakage current

# initializing the ZND

ZND = RS_ZND('TCPIP::192.168.1.149::INSTR', reset=True) 
ZND.TwoPort()
ZND.SetSweepfrequency(start_freq, stop_freq, freq_points)

ZND.SetPower(power) #[db] minimum -30db
ZND.SetIFBW(1e3) #Set IF bandwidth in Hz
ZND.SetSweepTime(SweepTime)

ZND.AutoScale()

# initializing the temperature reading 
tempdev = He7Temperature(addr='192.168.1.249',verb=False)
temp = 0

#############################################################
''' measurements '''
# generating gate pattern
pattern = gate_pattern(target_gate=target_gate, mode='single', data_points=gate_points, shift_voltage= shift_voltage )
print ('gate pattern:', pattern)

# modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

ramp_time = np.abs(np.floor(shift_voltage/ramp_spead))
dev.RampVoltage(DAC,1000*shift_voltage/s1h_gain,tt=ramp_time) # the factor 1000 is applied as the unit reads in mV.


gate_voltage_step = pattern['ramp_pattern'][1]-pattern['ramp_pattern'][0]
ramp_time = np.abs(np.floor(gate_voltage_step/ramp_spead))

S21dB = np.array([],[])
S21Ph = np.array([],[])
gate = np.array([])
Leakage_current = np.array([])
Temp = np.array([])

dev.RampVoltage(DAC,pattern['ramp_pattern'][0],tt=ramp_time)

for count,gate_voltage in enumerate(pattern['ramp_pattern']): # ramping up the gate voltage
	print (gate_voltage)
	dev.RampVoltage(DAC,1000*gate_voltage/s1h_gain,tt=ramp_time) # the factor 1000 is applied as the unit reads in mV.
	print ("voltage set")
	
	if watch_gate_leakage: 
		leakage_current = 1e9*gate_leakage_v_I_conversion*float(vmeasure.query('READ?')) # in the units of [nA]
	else: 
		leakage_current = 0
	
	Leakage_current = np.append(Leakage_current,leakage_current)
	

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
	print ("ZND measurement start")
	data = ZND.MeasureScreen_pd()
	print ("ZND measurement finished")


	if count == 0:
		S21dB = np.array(data['S21dB (dB)'])
		S21Ph = np.array(data['S21Ph (rad)'])
		gate = np.array(gate_voltage)
	else: 
		S21dB = np.array(np.vstack((S21dB,data['S21dB (dB)'])))
		S21Ph = np.array(np.vstack((S21Ph,data['S21Ph (rad)'])))
		gate = np.array(np.append(gate,gate_voltage))

		plt.rcParams["figure.figsize"] = [16,9]
		
		if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
			plt.subplot(2, 1, 1)
			plt.plot(data['Frequency (Hz)'],data['S21dB (dB)'])
			plt.ylabel('S21dB (dB)')
			plt.text(60, .025,['Gate: ', gate_voltage , 'V'])
		
		plt.subplot(2, 1, 2)
		plt.contourf(data['Frequency (Hz)'],gate,S21dB)
		plt.ylabel('gate voltage (V)')
		plt.title('S21dB (dB)')
		plt.xlabel('Frequency (Hz)')

		print ("plotting finished")

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

if watch_gate_leakage:
	vmeasure.close()

print('FINISHED')    

#############################################################
''' output '''

if save_data:

	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
	Data.close()
	plt.close()

	
	print('gate =', gate)
	plt.subplot(2, 1, 1)
	plt.plot(gate,Leakage_current)
	plt.ylabel('leakage current (nA)')
	plt.xlabel('gate (V)')
	
	plt.subplot(2, 1, 2)
	plt.plot(gate,Temp)
	plt.ylabel('temperature (K)')
	plt.xlabel('gate (V)')
	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix+'_extra')







 




