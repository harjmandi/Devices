''' This program uses R&S ZNB VNA to detect the resonace of a microwave cavity and HF2LI (very low amplitude of 77uV and low frequency to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).



    Hardware to be used:
        - R&S ZNB VNA
        - HF2LI: For gating



'''

import serial
import pyvisa
import os
import numpy as np
import time
import zhinst.utils

import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import stlab
import stlabutils

from stlab.devices.RS_ZND import RS_ZND
from HF2LI_ApplyGate import gate_it 


def ramp_gate(target_gate,current_gate, initialize):

    gate_array = np.arange(current_gate,target_gate,gate_step)
    
    if target_gate < current_gate:
        gate_array = np.arange(current_gate,target_gate,-gate_step)

    gate_array = np.append(gate_array,target_gate)
    for gate in gate_array:
        gate_it(device_id, gate, out_channel, device, daq, out_mixer_channel, out_range = gate_range, frequency = frequency, amplitude =amplitude, initialize = initialize)
        time.sleep(gate_step/ramp_spead)

    return target_gate

###############################################################################################
''' Definitions'''

#definitions
title = 'A0_firstDevice'
path = 'C:\\Users\\Localuser\\Documents\\DATA\\Hadi\\01_Lab Journals\\A_Nonlinearity in graphene resonators\\A0 2020-10-27 measurements'

time_sleep = 1 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 0.5 # [V/s] the safe spead for ramping the gate voltage 
start_gate = 4 #
stop_gate = 9
gate_points = 100
gate_step = 0.2 # [V] minimum gata steps for ramping
gate_range = 10 # [V] output range set on the HF2LI, acceptable values: 10e-3,100e-3,1,10
frequency = 0.1 # [Hz] modulation frequency of the gate, the smaller the better
amplitude = 50e-6 #[V] modulated amplitude of the gate
out_channel = 2 # channel used for gating on HF2LI

monitor_ratio = 7 #shows 1 out of "monitor_ratio" spectrums
show_figure = True

start_freq = 1  # start grequency [MHz]
stop_freq = 50 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 1001 # frequency sweep points
#IF bandwidth= 1000, this is for my own records and does not affect the VNA settings.

power = 5 #sweep power [dB] range: -45 to 3 dB
averaging  = 1

frequency_pattern = np.linspace(start_freq, stop_freq, freq_points)
gate_pattern = np.linspace(start_gate,stop_gate, gate_points)



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

colnames = ['Frequency (Hz)', 'S21re ()', 'S21im ()', 'S21dB (dB)', 'S21Ph (rad)', 'Power (dBm)', 'Time (s)', 'Gate Voltage (V)', 'S21 (uW)']
Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)

##########################################################
''' Initializing the devices '''



# HF2LI settings
device_id = 'DEV1684'
output_amplitude = 77e-6 #measurement amplitude [V]
measure_output_channnel = 1
measure_frequency = 0.1 #[Hz]

(daq, device, props) = zhinst.utils.create_api_session(device_id, 1, required_devtype='.*LI|.*IA|.*IS')
zhinst.utils.api_server_version_check(daq)
zhinst.utils.disable_everything(daq, device)
out_mixer_channel = zhinst.utils.default_output_mixer_channel(props)
current_gate = 0
current_gate = ramp_gate(start_gate,current_gate, initialize = True)


# initializing the ZND
VNA = RS_ZND('TCPIP::192.168.10.151::INSTR', reset=False)
# VNA.SetSweepfrequency(start_freq, stop_freq, freq_points)
# VNA.SetPower(power) #[db] minimum -30db
# VNA.SetIFBW(1e3) #Set IF bandwidth in Hz
# VNA.SetSweepTime(SweepTime)

# VNA.AutoScale()
# # VNA.write('INST:SEL "NA"')  #set mode to Network Analyzer
# if measure == 'OnePort':
#   VNA.SinglePort()
# elif measure == 'TwoPort':
#   VNA.TwoPort()



# if averaging > 1:
#   VNA.write('SENS:AVER:COUN %d' % averaging)
#   # VNA.write('SENS:AVER ON')
#   # VNA.write('SENS:AVER:CLEAR')


#############################################################
''' measurements '''
# amping to the target  gate
S_amp_Watt = np.array([],[])
S_phase = np.array([],[])
time_array = np.array([])


STOP = False
            

t_in = time.time()



count = 0
for count, gate_voltage in enumerate(gate_pattern):
    if STOP:
        break

    current_gate = ramp_gate(gate_voltage,current_gate, initialize = False)
    time.sleep(time_sleep)

    print ('_______________________________')
    print ('gate count {:d} set'.format(count))
    print('gate voltage {:.2f} set'.format(gate_voltage))

    data = VNA.MeasureScreen_pd()
    amp_data = np.array(data['S21dB (dB)'])
    amp_data_Watt = 10**(amp_data/20)*1e6
    phase_data = np.array(data['S21Ph (rad)'])

    t = time.time() - t_in


    if count == 0:

        S_amp_Watt = amp_data_Watt
        S_phase = phase_data
        time_array = t

    else:

        S_amp_Watt = np.array(np.vstack((S_amp_Watt,amp_data_Watt)))
        S_phase = np.array(np.vstack((S_phase,phase_data)))
        time_array = np.append(time_array,t)


        plt.rcParams["figure.figsize"] = [16,9]

        if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
            plt.subplot(2, 2, (1,3))
            plt.plot(data['Frequency (Hz)']*1e-6,amp_data_Watt)
            plt.ylabel('S11 (uW)')
            plt.xlim(np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6)
            plt.title(title + ' Power: '+ str(power) + ' dBm')



        plt.subplot(2, 2, (2,4))

        if count > 0:
            extent = [np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6, gate_pattern[0], gate_pattern[count]]
            plt.imshow(S_amp_Watt, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = np.min(np.min(S_amp_Watt)), vmax = np.max(np.max(S_amp_Watt)))



        plt.ylabel('Gate Voltage (V)')
        plt.title('S11 (uW)')
        plt.xlabel('Frequency (MHz)')



    if show_figure:
        plt.pause(0.5)


    if save_data:

        data['Power (dBm)'] = VNA.GetPower()
        data['Time (s)'] = t
        data['Gate Voltage (V)'] = gate_voltage
        data['S21 (uW)'] = amp_data_Watt

        stlab.savedict(Data, data)




    print('ELAPSED TIME: {:.2f} min'.format(t/60))



    for cnt in range(1000):
        for event in pygame.event.get(): # stopping if 's' pressed
            if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
                STOP = True
                print('--------------------------------')
                print('Stop command detected!')
                print('--------------------------------')
                ramp_gate(0, current_gate,initialize = False)
                break

ramp_gate(0, current_gate,initialize = False)
stlab.metagen.fromarrays(Data,frequency_pattern,gate_pattern[0:count+1],xtitle='frequency (MHz)', ytitle='gate voltage (V)',ztitle='',colnames=colnames)
#############################################################
''' output '''

if save_data:

    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
    Data.close()
    plt.close()


#############################################################
''' finishing '''

print('FINISHED')

