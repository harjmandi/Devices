''' This program uses R&S ZNB VNA to detect the resonace of a microwave cavity and TENMA to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).



    Hardware to be used:
        - R&S ZND VNA
        - Keysight B2961A: For gating



    Before runnign the programm:

    Wiring:
        -   For the reflection measurements with the directional-coupler inside the fridge: Out put of the KEYSIGHT FieldFox (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
            eventually connected to the Port 2 on KEYSIGHT FieldFox (through the circulator and low-T amplifier) and "input" port to the resonator.

        - The address of the Keithley changes in each measurements. Before running the measurements check the Device Manager for USB-to-Serial Comm Port and modify the number in "ASRL5::INSTR" on line 139.  

'''

import serial
import pyvisa
import os
import numpy as np
import time

import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
import stlab
import stlabutils

from stlab.devices.RS_ZND import RS_ZND



###############################################################################################
''' Definitions'''

#definitions
title = 'A44_5-2_5p3_01_'
path = 'C:\\Users\\Hadi\\surfdrive\\01_Lab Journals\\A_Nonlinearity in graphene resonators\\A44 2021-03-15 measurements\\Day 1'



monitor_ratio = 5 #shows 1 out of "monitor_ratio" spectrums
show_figure = True

start_freq = 25  # start grequency [MHz]
stop_freq = 80 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 2501 # frequency sweep points
#IF bandwidth= 10k, this is for my own records and does not affect the VNA settings.

Voltage = 10 #sweep power [dB] range: -45 to 3 dB

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

colnames = ['Frequency (Hz)', 'S21re ()', 'S21im ()', 'S21dB (dB)', 'S21Ph (rad)', 'Power (dBm)', 'Time (s)', 'Gate Voltage (V)', 'S21 (uW)']
Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)

##########################################################
''' Initializing the devices '''

# TENMA setting
rm = pyvisa.highlevel.ResourceManager() # Opens the resource manager and sets it to variable rm
gate_dev = rm.open_resource("ASRL5::INSTR", baud_rate = 9600, data_bits = 8)

gate_dev.write_termination = '\n'
gate_dev.read_termination = '\n'
gate_dev.send_end = True
gate_dev.StopBits = 1
SetRemote(gate_dev)





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
ramp_time = np.abs(np.floor(start_gate/ramp_spead))
TurnOn(gate_dev)
RampVoltage(gate_dev, start_gate,tt=ramp_time, steps = 100)
print('gate set')

S_amp_Watt = np.array([],[])
S_phase = np.array([],[])
time_array = np.array([])


STOP = False
            

t_in = time.time()



count = 0
for count, gate_voltage in enumerate(gate_pattern):
    if STOP:
        break
    try:
        RampVoltage(gate_dev, gate_voltage,tt=2, steps = 10)
        print ('_______________________________')
        print ('gate count {:d} set'.format(count))
        print('gate voltage {:.2f} set'.format(gate_voltage))

        # VNA.MeasureScreen_pd()
        data = VNA.MeasureScreen_pd() #for parametric measurement we need to measure twice. 
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


            plt.rcParams["figure.figsize"] = [12,7]

            if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
                plt.subplot(2, 2, (1,3))
                plt.plot(data['Frequency (Hz)']*1e-6,amp_data_Watt)
                plt.ylabel('S11 (uW)')
                plt.xlabel('Frequency (MHz)')
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
                    RampVoltage(gate_dev,0,tt=ramp_time) # to safely return back the gate voltage
                    break
                    print('--------------------------------')
                    print('s detected')
                    print('--------------------------------')

    except:
        Close(gate_dev)
        print ('############gate_dev closed#################')





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
RampVoltage(gate_dev,0,tt=ramp_time) # to safely return back the gate voltage
SetLocal (gate_dev)
# gate_dev.close()
# # Close(gate_dev)