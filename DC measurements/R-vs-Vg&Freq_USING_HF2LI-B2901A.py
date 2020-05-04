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
from my_poll_v2 import R_measure as R_measure
import stlab
import os
from stlab.devices.Keysight_B2901A import Keysight_B2901A
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import math


#############################################################
''' Definitions'''

# definitions
tempdev = 3.4
prefix = 'C26_FE_UL_SCHEME1_Rb1M_BOXResistor'
path = 'D:\\measurement_data_4KDIY\\Hadi\\C26 2020-04-10 measurements'

time_step = 0.1 #time step between each gate voltage steps, to stablize the gate
ramp_speed = 500 # the safe speed for ramping the gate voltage [mV/s]
target_gate = 42
gate_points = 100

safe_gate_current = 20e-3 # [A], safe current leakage limit. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!
gate_pattern = np.linspace(-target_gate, target_gate, gate_points)
monitor_ratio = 1

# HF2LI settingsl;mkln
measure_amplitude = 10 #measurement amplitude [V]
start_freq = 24.5e6
end_freq = 25.2e6
pt_freq = 50
measure_output_channnel = 1
measure_input_channnel = 1
demodulation_time_constant = 0.1
deamodulation_duration = 0.18

measure_frequency = np.linspace(start_freq, end_freq,pt_freq) #[Hz]

bias_resistor = 1e6

# Calibration parameters; experimentally achieved to adjst the resistance reading
    # CASE 1: bias resistance of 1M and demodulation_time_constant = 0.1 =>> calibration_factor = 1.45 and shift = 0
    # CASE 2: bias resistance of 10M and demodulation_time_constant = 0.45 =>> calibration_factor = 0.65 and shift = 400


calibration_factor = 1 # 1.45 recommended  with bias resistance of 1M and demodulation_time_constant = 0.1 # to compensate the shift in resistance measurement
shift = 0
in_range = 2

out_range = 10

diff = True
add = False
offset = 0
ac = False

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
(daq, device, props) = zhinst.utils.create_api_session('dev352', apilevel_example, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)


# Keysight setting
gate_dev = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
gate_dev.SetModeVoltage()
gate_dev.SetOutputOn()
gate_dev.SetComplianceCurrent(safe_gate_current)


#############################################################
''' MEASUREMENT'''


# Resistance measurement while modulating the gate voltage
count = 0 # couter of step numbers
leakage_current = 0

if save_data:
    colnames = ['step ()','gate voltage (V)','leakage current (nA)','Vin (V)', 'Impedence (ohm)', 'phase ()', 'demodulation duration (s)', 'X (V)', 'Y (V)']
    my_file= stlab.newfile(prefix,'_',autoindex=True,colnames=colnames, mypath= path)
    stlab.metagen.fromarrays(my_file,measure_frequency,-gate_pattern,[],xtitle='frequency (Hz)', ytitle='gate voltage (V)', ztitle='', colnames=colnames)



ramp_time = np.abs(np.floor(gate_pattern[0]/ramp_speed))
gate_dev.RampVoltage(gate_pattern[0],tt=2*ramp_time, steps = 100)


ramp_time = 0.5
plt_Vg=np.array([])
plt_resistance=np.array([])
plt_phase=np.array([])


END = False

for count,gate_voltage in enumerate(gate_pattern): # ramping up the gate voltage
    gate_dev.RampVoltage(gate_voltage,tt=ramp_time, steps = 5)
    leakage_current = float(gate_dev.GetCurrent()) # in the units of [A]
    print ('\n\n------------------------')


    single_Vin = np.array([])
    single_Phase = np.array([])



    for count_fre, freq in enumerate(measure_frequency):

        for event in pygame.event.get():
            if event.type == QUIT:sys.exit()
            elif event.type == KEYDOWN and event.dict['key'] == 101:
                END = True

        if END:
            break


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


        Vin = np.abs(measured[4] + 1j*measured[5])
        # r = Vin * bias_resistor/(measure_amplitude - Vin) # thie relation is valid when the phase is close to zero.
        measured [0] = Vin

        line = [count,gate_voltage, leakage_current] + measured

        if save_data:
            stlab.writeline(my_file,line)


        single_Vin = np.append(single_Vin, Vin)
        single_Phase = np.append(single_Phase, measured [2])

    if END:
        break


    if count == 0:

        map_Vin = single_Vin
        map_Phase = single_Phase


    else:

        map_Vin = np.array(np.vstack((map_Vin,single_Vin)))
        map_Phase = np.array(np.vstack((map_Phase,single_Phase)))


    plt.rcParams["figure.figsize"] = [16,9]

    if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
        plt.subplot(4, 1, 1)
        # plt.title(prefix+ ", V = {:.1f}, R(bias) = {:.2f} $k\Omega$, ".format(measure_amplitude, bias_resistor/1e3))
        plt.plot(measure_frequency*1e-6,single_Vin)
        plt.ylabel('Vin (V)')
        plt.xlim(np.min(measure_frequency)*1e-6,np.max(measure_frequency)*1e-6)


        plt.subplot(4, 1, 2)
        plt.plot(measure_frequency*1e-6,single_Phase)
        plt.ylabel('Phase (°)')
        plt.xlim(np.min(measure_frequency)*1e-6,np.max(measure_frequency)*1e-6)

    print('count:', count)
    print('gate:', gate_voltage)
    print('Map Vin shape:',map_Vin.shape)
    print('Map pahse shape:',map_Phase.shape)
    print('measured gate:',gate_pattern[0:count+1])


    if count > 0:
        plt.subplot(4, 1, 3)
        plt.title('Vin (V)', backgroundcolor = 'white')
        plt.contourf(measure_frequency*1e-6,gate_pattern[0:count+1],map_Vin)
        plt.ylabel('Vg (V)')

        plt.subplot(4, 1, 4)
        plt.title('Phase (°)', backgroundcolor = 'white')
        plt.contourf(measure_frequency*1e-6,gate_pattern[0:count+1],map_Phase)
        plt.ylabel('Vg (V)')
        plt.xlabel('Frequency (MHz)')

    plt.pause(0.1)



print('RAMPING FINISHED')
gate_dev.RampVoltage(0,tt=ramp_time*10) # to safely return back the gate voltage
gate_dev.SetOutputOff()
print('FINISHED')
zhinst.utils.disable_everything(daq, device)


#######################################################################
''' saving the data '''

if save_data:

    # saving the metafile
    plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix)
    my_file.close()

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
    # my_file= stlab.newfile(prefix,'_metadata',autoindex=False,colnames=parameters,usefolder=False,mypath = os.path.dirname(my_file.name),usedate=False)
    # stlab.writeline(my_file,parameters_line)

    # saving the plots
    title = 'Resistance'
    caption = ''
    stlab.autoplot(my_file,'gate voltage (V)','Resistance (k ohm)',title=title,caption=caption)
    title = 'Phase'
    caption = ''
    stlab.autoplot(my_file,'gate voltage (V)','phase ()',title=title,caption=caption)
    title = 'Duration'
    caption = ''
    stlab.autoplot(my_file,'gate voltage (V)','demodulation duration (s)',title=title,caption=caption)
    title = 'Leakage Current'
    caption = ''
    stlab.autoplot(my_file,'gate voltage (V)','leakage current (nA)',title=title,caption=caption)





