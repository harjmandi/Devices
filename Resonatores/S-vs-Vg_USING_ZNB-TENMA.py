''' This program uses R&S ZND VNA to detect the resonace of a microwave cavity and B2961A to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).



	Hardware to be used:
		- R&S ZND VNA
		- Keysight B2961A: For gating



	Before runnign the programm:
		- Make sure that room temperature amplifier is well wired: mounted on port 2 of the KEYSIGHT FieldFox and it is powered up with 15 V with Rigol

	Wiring:
		-	For the reflection measurements with the directional-coupler inside the fridge: Out put of the KEYSIGHT FieldFox (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
			eventually connected to the Port 2 on KEYSIGHT FieldFox (through the circulator and low-T amplifier) and "input" port to the resonator.

'''

import serial
import pyvisa 
import os
import numpy as np
import time

import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import stlabutils
import stlab
from TENMA import TENMA


from stlab.devices.RS_ZND import RS_ZND

# Functions NOTE: ideally this functions has to be intergrated into a TENMA class; but I did not manage to do that yet. so I put them here. 
def numtostr(mystr):
    return '%20.15e' % mystr
    
def SetVoltage(gate_device, Vol):
    mystr = numtostr(Vol)
    mystr = 'VSET1:' + mystr
    gate_device.write(mystr)

def GetVoltage(gate_device):  
        volt = gate_device.query('VOUT1?')
        return float(volt)

def RampVoltage(gate_device, mvoltage, tt=5., steps=100):  #To ramp voltage over 'tt' seconds from current DAC value.
    v0 = GetVoltage(gate_device)
    if np.abs(mvoltage - v0) < 1e-2:
        SetVoltage(gate_device,mvoltage)
        return
    voltages = np.linspace(v0, mvoltage, steps)
    twait = tt / steps
    for vv in voltages:
        SetVoltage(gate_device,vv)
        time.sleep(twait)

def GetCurrent(gate_device):  # (manual entry) Preset and make a DC current measurement with the specified range and resolution. The reading is sent to the output buffer.
        # range and res can be numbers or MAX, MIN, DEF
        # Lower resolution means more digits of precision (and slower measurement).  The number given is the voltage precision desired.  If value is too low, the query will timeout
        num = gate_device.query("IOUT1?")
        return float(num)

def TurnOn(gate_device):
    gate_device.write("OUT1")


def TurnOff(gate_device):
    gate_device.write("OUT0")

def Close(gate_device):
    gate_device.close()

###############################################################################################
''' Definitions'''

#definitions
title = 'C26_LL_GateSweep_'
path = 'F:\\measurement_data_triton\\Hadi\\C\\C26 2020-06-26 measurements'
figures_path = path+'/All_Results'

time_step = 1#20 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 10 # the safe spead for ramping the gate voltage [mV/s]
min_gate = -15 #
max_gate = 15
gate_points = 500

monitor_ratio = 10 #shows 1 out of "monitor_ratio" spectrums
safe_gate_current = 5e-3 # [A], safe current leakage limit, above this limit S1h unit gives an error. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!

start_freq = 4.7737  # start grequency [MHz]
stop_freq = 5.3889 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 1001 # frequency sweep points
#IF bandwidth= 1000, this is for my own records and does not affect the VNA settings.

power = -45 #sweep power [dB] range: -45 to 3 dB
measure = 'TwoPort' # 'OnePort' or 'TwoPort'
averaging  = 1

frequency_pattern = np.linspace(start_freq, stop_freq, freq_points)




# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False

prefix = title+'_GateSweep'

font = {'family': 'serif',
		'color':  'darkred',
		'weight': 'normal',
		'size': 16,
		}

measure_frequency = np.linspace(start_freq,stop_freq,freq_points)


##########################################################
''' Initializing the devices '''

# TENMA setting
rm = pyvisa.highlevel.ResourceManager()	# Opens the resource manager and sets it to variable rm
gate_dev = rm.open_resource("ASRL8::INSTR", baud_rate = 9600, data_bits = 8)
gate_dev.write_termination = '\n'
gate_dev.read_termination = '\n'
gate_dev.send_end = True
gate_dev.StopBits = 1
print('here')
print(gate_dev.query("*IDN?"))
print('here')

# initializing the ZND
VNA = RS_ZND('TCPIP::192.168.10.151::INSTR', reset=False)
# VNA.SetSweepfrequency(start_freq, stop_freq, freq_points)
# VNA.SetPower(power) #[db] minimum -30db
# VNA.SetIFBW(1e3) #Set IF bandwidth in Hz
# VNA.SetSweepTime(SweepTime)

# VNA.AutoScale()
# # VNA.write('INST:SEL "NA"')  #set mode to Network Analyzer
# if measure == 'OnePort':
# 	VNA.SinglePort()
# elif measure == 'TwoPort':
# 	VNA.TwoPort()



# if averaging > 1:
# 	VNA.write('SENS:AVER:COUN %d' % averaging)
# 	# VNA.write('SENS:AVER ON')
# 	# VNA.write('SENS:AVER:CLEAR')


#############################################################
''' measurements '''
# generating gate pattern
gate_pattern = np.linspace(min_gate, max_gate,gate_points)
# modulating the gate voltage
ramp_time = np.abs(np.floor(gate_pattern[0]/ramp_spead))
gate_dev.RampVoltage(gate_pattern[0],tt=10*ramp_time, steps = 100)
gate_voltage_step = gate_pattern[1]-gate_pattern[0]
ramp_time = np.abs(np.floor(gate_voltage_step/ramp_spead))


count = 0 # couter of step numbers
leakage_current = 0

S21dB = np.array([],[])
S21Ph = np.array([],[])
gate = np.array([])
Leakage_current = np.array([])

t_in = time.time()
for count,gate_voltage in enumerate(gate_pattern): # ramping up the gate voltage


	gate_dev.RampVoltage(gate_voltage,tt=ramp_time, steps = 5)

	leakage_current = float(gate_dev.GetCurrent()) # in the units of [A]
	Leakage_current = np.append(Leakage_current,leakage_current)

	# if np.abs(leakage_current) > safe_gate_current:
	# 	GATE_LEAKAGE = True
	# 	print ('gate current', leakage_current, ' nA exceeds safe gate current limit reaching the gate voltage of', gate_voltage, 'V.')
	# 	print ('dielectric resitance is only', oxide_resistance, 'MOhms.')
	# 	print ('reseting the gate voltage')
	# 	dev.RampVoltage(DAC,0,tt=ramp_time)
	# 	break
	# print ('\n\n------------------------')


	time.sleep(time_step)

	for j in range(averaging):
		data = VNA.MeasureScreen_pd()
		for event in pygame.event.get(): # stopping if 's' pressed
			if event.type == QUIT: sys.exit()
			if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
				STOP = True
				gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage
				break
		if STOP:
			break

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
			plt.subplot(2, 2, 1)
			plt.plot(data['Frequency (Hz)']*1e-9,amp_data)
			plt.ylabel('S11dB (dB)')
			plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)
			plt.title(title + ' Power: '+ str(power) + ' dBm')

			plt.subplot(2, 2, 3)
			plt.plot(data['Frequency (Hz)']*1e-9,phase_data*180/np.pi)
			plt.ylabel('Phase (°)')
			plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)
			plt.xlabel('frequency (GHz)')



		plt.subplot(2, 2, (2,4))

		if count > 0:
			extent = [np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9, gate_pattern[0], gate_pattern[count]]
			plt.imshow(S_amp, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = -38, vmax = -22)

		plt.ylabel('$V_g$ (V)')
		plt.title('S11dB (dB)')
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
			colnames = ['Vset (V)', 'Imeas (A)', 'R (Ohm)', 'Vgate (V)', 'T (K)', 'Ileakage (nA)']

			Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)



		stlab.savedict(Data, data)


	if STOP:
		break


	t = time.time()
	print('measured gate steps:', count+1)
	time_passed = t - t_in
	time_remain = (time_passed/(count+1))*(len(gate_pattern)-count-1)
	print('ELAPSED TIME: {:.2f} min'.format(time_passed/60))
	print('REMAINING TIME: {:.2f} min'.format(time_remain/60))


gate_dev.RampVoltage(0,tt=ramp_time) # to safely return back the gate voltage
stlab.metagen.fromarrays(Data,frequency_pattern,gate_pattern[0:count+1],xtitle='frequency (Hz)', ytitle='gate voltage (V)',ztitle='',colnames=colnames)

print('FINISHED')

#############################################################
''' output '''

if save_data:

	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
	# plt.savefig(figures_path+'\\'+str(start_freq)+'GHz.jpg')

	Data.close()
	plt.close()


	plt.plot(gate_pattern[0:count+1],Leakage_current)
	plt.ylabel('leakage current (nA)')
	plt.xlabel('gate (V)')
	plt.savefig(os.path.dirname(Data.name)+'\\'+prefix+'leakage_current')





