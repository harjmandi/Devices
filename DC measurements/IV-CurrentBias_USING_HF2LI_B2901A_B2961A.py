''' This program is for IV measurement (I bias) using a lock-in amplifier.
A DC Voltage is added to the AC using an external circuit including a bias resistor (can be chosen, normally <100KOhm) and capacitor (22uF).
Keysight 2961A provided the gate Voltage.

'''



import stlab
import zhinst.utils
import stlabutils
from my_poll_v2 import R_measure as R_measure
import datetime
import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
from matplotlib.pyplot import subplots, show

import os
import math
from stlab.devices.Keysight_B2901A import Keysight_B2901A
from stlab.devices.keysightB2961A import keysightB2961A as Keysight_B2961A




''' input '''
prefix = 'F20_IV_h3-3to4-floating12_IBias_HF2LI'
path = 'D:/measurement_data_4KDIY/Hadi/F20 2020-05-30 measurements/'

i_BiasMax = 0.10e-6 # Maximum bias current [A]
i_BiasMin = -i_BiasMax # Minimum bias current [A]
delta_i_bias = 5e-9#7e-9 # Delta bias current, used to be 2e-6 for the failed experiment
i_oss = 5e-9 # Oscilation amplitude [A]
R_bias = 10e6 #Bias resistance, to be set on the sample simulator


Vgmax = 40 # Maximum gate voltage [V]
Vgmin = -40 # Minimum gate voltage [V]
deltaVg = 20 # Gate voltage steps [V]
gate_ramp_speed = 1# 0.3 # Gate ramp speed [V/s], proposed: 0.3
time_sleep = 1 #sleep time to stablize the gate [s], proposed: 1

T = 3.38 #Temperature reading

# Lock in parameters
in_range = 100e-3 # musct be larger than 1mV
out_range = 10e-3 # possible ranges: 10e-3, 100e-3, 1, 10
measure_frequency = 797 #[Hz]
BW = 79.46e-3
filter_order = 1
demod_rate = 56.22
poll_length = 2 # must be few times larger than the demodulation_time_constant = 0.1/BW
diff = True
calibration_factor = 1.45


''' Initialize '''
# initial checks
if (i_BiasMax*R_bias > 42):
	print('The B2901A unit cannot provide the intended maximum current!')
	exit()

if (i_oss*R_bias>out_range):
	print('The output range is insufficient!')
	exit()

if (np.abs(i_BiasMax) > 2.7e-3 ) or (np.abs(i_BiasMin) > 2.7e-3 ):
	print('Input current to graphene is out of the safe range!')
	exit()


pygame.init()
pygame.display.set_mode((100,100))


## HF2LI
measure_amplitude = i_oss*R_bias #measurement amplitude [V]
measure_output_channnel = 1
measure_input_channnel = 1
# demodulation_time_constant = 0.02 #=real filtering time constant is 10 times longer! => Filtering BW = 0.1/Tc

add = False
offset = 0
ac = False

apilevel_example = 6  # The API level supported by this example.
(daq, device, props) = zhinst.utils.create_api_session('dev352', apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)


# Keysight for V_DC
B2901A = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
B2901A.SetModeVoltage()
B2901A.write('SENS:CURR:PROT 0.002') #set the current compliance limit to 10mA
B2901A.SetOutputOn()

# Keysight for gating
B2961A = Keysight_B2961A('TCPIP::192.168.1.50::INSTR')
B2961A.SetModeVoltage()
B2961A.SetComplianceCurrent(10e-9)
B2961A.SetOutputOn()


## Calculation
Vg_list = np.linspace(Vgmin,Vgmax,int((Vgmax-Vgmin)/deltaVg)+1)
iBiaslist = np.linspace(i_BiasMax, i_BiasMin, int((i_BiasMax-i_BiasMin)/delta_i_bias)+1)


Vg_ini = Vg_list[0]
print('Ramping up the Keysights')
if np.abs(Vg_ini) > 0.2:
	B2961A.RampVoltage(Vg_ini,tt=np.abs(Vg_ini/gate_ramp_speed), steps = 100) ##ramping to the
if np.abs(iBiaslist[0]) > 50e-9:
	B2901A.RampVoltage(iBiaslist[0]*R_bias,tt=10, steps = 30)

print('Wait {:.0f}s for stablization'.format(5*time_sleep,Vg_ini))
time.sleep(5*time_sleep)

END = False

resistance_array = np.array([])
I_leakage_array = np.array([])
V_array = np.array([])



## Output setting
idstring = 'bias_current{:.0f}mA'.format(i_BiasMax*1e3).replace('.','p')
colnames = ['Iset (A)', 'Vmeas (V)', 'Rmeas (Ohm)', 'Vgate (V)', 'Vg_actual (V)','Leakage Current (A)', 'T (K)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)
stlab.metagen.fromarrays(myfile,iBiaslist,Vg_list,zarray=[],xtitle='bias current (A)',ytitle='gate Voltage (V)',ztitle='',colnames=colnames)


plt.rcParams["figure.figsize"] = [16,9]
fig, (ax1,ax2, ax3)= subplots(3, 1, sharex = True)

for cnt in range(3):
	R_measure(device_id = 'dev352',
				amplitude= measure_amplitude,
				out_channel = measure_output_channnel,
				in_channel = measure_input_channnel,
				BW = BW,
				filter_order = filter_order,
				demod_rate = demod_rate,
				frequency = measure_frequency,
				poll_length = poll_length,
				device=device,
				daq=daq,
				out_mixer_channel=out_mixer_channel,
				bias_resistor=R_bias,
				in_range = in_range,
				out_range = out_range,
				diff = diff,
				add = add,
				offset = offset,
				ac = ac,
				initialize = True
				)


start_time = time.time()

for Vg_count,Vg in enumerate(Vg_list):

	B2961A.RampVoltage(Vg,tt=deltaVg/gate_ramp_speed, steps = 10) ##ramping this voltage in 20seconds
	print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep, Vg))
	B2901A.RampVoltage(iBiaslist[0]*R_bias,tt=10, steps = 30)
	time.sleep(time_sleep)
	Vg_actual = B2961A.GetVoltage()
	leakage_current = B2961A.GetCurrent()


	V_array = np.array([])
	R_array = np.array([])

	for i in iBiaslist:

		for event in pygame.event.get():
			if event.type == QUIT:sys.exit()
			elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
				END = True
				B2901A.RampVoltage(0,tt=10, steps = 20)
				if np.abs(Vg_actual) > 0.2:
					B2961A.RampVoltage(0,tt=60, steps = 40)

		if END:
		  break

		B2901A.RampVoltage(i*R_bias,tt=0.5, steps = 3)
		measured = R_measure(device_id = 'dev352',
			amplitude= measure_amplitude,
			out_channel = measure_output_channnel,
			in_channel = measure_input_channnel,
			BW = BW,
			filter_order = filter_order,
			demod_rate = demod_rate,
			frequency = measure_frequency,
			poll_length = poll_length,
			device=device,
			daq=daq,
			out_mixer_channel=out_mixer_channel,
			bias_resistor=R_bias,
			in_range = in_range,
			out_range = out_range,
			diff = diff,
			add = add,
			offset = offset,
			ac = ac
			)

		measured[0] = calibration_factor * measured[0]
		Resistance = measured[0]
		print ('resistance =', Resistance)
		Voltage = Resistance * i

		R_array = np.append(R_array,Resistance)
		V_array = np.append(V_array,Voltage)

		line = [i, Voltage, Resistance, Vg, Vg_actual, leakage_current, T]
		stlab.writeline(myfile, line)
		time.sleep(time_sleep/5)

	myfile.write('\n')

	if END:
		  break

	if Vg_count == 0:
		R_map = R_array
	else:
		R_map = np.vstack((R_map,R_array))

	elapsed_time = time.time()- start_time
	remaning_time = (Vg_list.size-Vg_count-1)*elapsed_time/(Vg_count+1)

	ax1.cla()
	ax1.set_title(prefix)
	ax1.set_ylabel('Voltage [mV]')
	ax1.plot(iBiaslist*1e3,V_array*1e3, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg_actual))
	ax1.legend()

	ax2.cla()
	ax2.plot(iBiaslist*1e3,R_array, '--',marker='.',markersize=2, linewidth=0.15, alpha=0.9, label = '{:.1f}Vg'.format(Vg_actual))
	ax2.legend()
	ax2.set_ylabel('dV/dI [$\Omega$]')
	# ax2.set_ylim([0, 2000])


	if Vg_count > 0:
		extent = [i_BiasMin*1e3,i_BiasMax*1e3, Vg_list[0], Vg_list[Vg_count]]
		ax3.imshow(R_map, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = 700, vmax = 2200)

	ax3.set_title('Elapsed time: '+ str(datetime.timedelta(seconds=elapsed_time)).split(".")[0]+ ',    remaning time: <'+ str(datetime.timedelta(seconds=remaning_time)).split(".")[0] )
	ax3.set_ylabel('$V_g$ (V)')
	ax3.set_xlabel('bias current (mA)')
	ax3.set_xlim([i_BiasMin*1e3,i_BiasMax*1e3])

	plt.pause(0.05)




plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
stlab.metagen.fromarrays(myfile,iBiaslist,Vg_list[0:Vg_count+1],zarray=[],xtitle='bias current (A)',ytitle='gate Voltage (V)',ztitle='',colnames=colnames)

# zhinst.utils.disable_everything(daq, device)
if END == False:
	B2901A.RampVoltage(0,tt=10, steps = 20)
	B2961A.RampVoltage(0,tt=60, steps = 40)

B2901A.close()
B2961A.close()



# saving suppelemntary plots
title = 'Resistance'
caption = ''
stlab.autoplot(myfile,'Iset (A)','Rmeas (Ohm)',title=title,caption=caption)
title = 'Leakage Current'
caption = ''
stlab.autoplot(myfile,'Iset (A)','Leakage Current (A)',title=title,caption=caption)

myfile.close()
