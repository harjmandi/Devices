# This program starts by measurign the internal resisatnce of the lock-in. The subtracts it from the later measurements. 


import numpy as np
import zhinst.utils
import time
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math
from my_poll_v2 import R_measure as R_measure



#############################################################
''' Definitions'''

# definitions

device_id = 'dev352'

# HF2LI settings
measure_amplitude = 0.1 #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
measure_frequency = 50e6 #[Hz]
demodulation_time_constant = 0.1
deamodulation_duration = 0.2

calibration_duration = 10 

calibration_factor = 1 # to compensate the shift in resistance measurement
shift = 0 


in_range = 100e-3 
out_range = 100e-3 
diff = False 
add = False 
offset = 0 
ac = False



bias_resistor = 1e6




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
Time=np.array([])
plt_resistance=np.array([])
plt_phase=np.array([])
plt_y = np.array([])
END = False

# measuring internal resisatnce
print('Calibration for internal resistances:')
input('Directly connect the output of the bias resistor to the Signal input port, press ENTER to continue ...')
t_ini = time.time()
t = 0
count = 0
X = 0
Y = 0

while t - t_ini < calibration_duration:
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

	X+= measured[4]
	Y+= measured[5]
	count+= 1
	t = time.time()


X = X/count
Y = Y/count

print ('Calibration Finished with average X = {:.2f}uV and Y = {:.2f}uV'.format(1e6*X, 1e6*Y))
h = input ('Connect to the device, press Enter to continue or "e" to exit.' )

if h == "e":
    sys.exit(0)

while (not END):

	mytime = time.time() - INI_time
			
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

	 

	plt_resistance = np.append(plt_resistance,measured_R)
	plt_y = np.append(plt_y,measured_y)
	plt_phase = np.append(plt_phase,measured_phi)
	
	Time = np.append(Time,mytime)

	plt.rcParams["figure.figsize"] = [12,6]

	
	plt.subplot(3, 1, 1)
	plt.plot(Time,plt_resistance*1e-3, '--r',marker='o')

	plt.ylabel('Resistance ($k\Omega$)')
	# plt.yscale('log')
	plt.title("Resistance = %4.2f k$\Omega$" %(measured[0]*1e-3))
	if mytime > 10:
		plt.xlim(mytime-10, mytime)
	
	
	plt.subplot(3, 1, 2)
	plt.plot(Time,plt_y*1e-3, '--r',marker='o')

	plt.ylabel('Resistance ($k\Omega$)')
	# plt.yscale('log')
	plt.title("Resistance = %4.2f k$\Omega$" %(measured[0]*1e-3))
	if mytime > 10:
		plt.xlim(mytime-10, mytime)
	

	plt.subplot(3, 1, 3)
	plt.plot(Time,plt_phase, '--r', marker='o')
	plt.ylabel('phase ()')
	plt.xlabel('time (s)')
	plt.title("phase = %4.2f ()" %(measured[2]))

	if mytime > 10:
		plt.xlim(mytime-10, mytime)

	plt.pause(0.1)

	for event in pygame.event.get():
		if event.type == QUIT:sys.exit()
		elif event.type == KEYDOWN and event.dict['key'] == 101:
			END = True


	
zhinst.utils.disable_everything(daq, device)

#######################################################################
''' saving the data '''


