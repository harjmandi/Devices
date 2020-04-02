
import numpy as np
import zhinst.utils
import time
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math
from my_poll_v2 import R_measure as R_measure
import stlab
import os


#############################################################
''' Definitions'''

# definitions

device_id = 'dev352'
prefix = 'R2p4k-C0uf'

path = 'D:/measurement_data/Hadi/C- Remote sensing of graphene/Cna 2020-03-16 measurements'

# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = np.linspace(10,1e6,101) #[Hz]

demodulation_time_constant = 0.1
deamodulation_duration = 0.18

calibration_factor = 1 # to compensate the shift in resistance measurement
shift = 0 
bias_resistor = 1e6

in_range = 1000e-3 
out_range = 1000e-3 
diff = True 
add = False 
offset = 0 
ac = False

save_data = True

if save_data:
	colnames = ['frequency (Hz)','resistance (ohm)','impedence (ohm)','phase ()', 'demodulation duration (s)', 'Vx (V)', 'Vy (V)']
	my_file = stlab.newfile(prefix,'_',autoindex=True,colnames=colnames, mypath= path)


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



#############################################################
''' MEASUREMENT'''
INI_time = time.time()
Freq=np.array([])
plt_resistance=np.array([])
plt_phase=np.array([])
END = False

for freq in measure_frequency:
		
	measured = R_measure(device_id = 'dev352', 
		amplitude = measure_amplitude, 
		out_channel = measure_output_channnel, 
		in_channel = measure_input_channnel, 
		time_constant = demodulation_time_constant, 
		frequency = freq, 
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

	measured[0] = calibration_factor * np.abs(measured[0]) + shift
	
	if save_data:
		stlab.writeline(my_file,[freq] + measured)

	
	plt_resistance = np.append(plt_resistance,measured[0])
	plt_phase = np.append(plt_phase,measured[2])
	Freq = np.append(Freq,freq)

	

	plt.rcParams["figure.figsize"] = [12,6]

	
	plt.subplot(2, 1, 1)
	plt.plot(Freq,plt_resistance*1e-3, '--r',marker='o')

	plt.ylabel('Resistance ($k\Omega$)')
	plt.yscale('log')
	plt.title("Resistance = %4.2f k$\Omega$" %(measured[0]*1e-3))

	plt.subplot(2, 1, 2)
	plt.plot(Freq,plt_phase, '--r', marker='o')
	plt.ylabel('phase ()')
	plt.xlabel('frequency (s)')
	plt.title("phase = %4.2f (), x = %4.2f (nV), y = %4.2f (nV)" %(measured[2], measured[4]*1e9, measured[5]*1e9))

	plt.pause(0.1)

	for event in pygame.event.get():
		if event.type == QUIT:sys.exit()
		elif event.type == KEYDOWN and event.dict['key'] == 101:
			END = True
	if END:
		break


	
zhinst.utils.disable_everything(daq, device)
if save_data:
	plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
	my_file.close()


#######################################################################
''' saving the data '''


