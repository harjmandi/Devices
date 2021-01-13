''' This program uses R&S ZNB VNA to detect the resonace of a microwave cavity 
The program eventually plots the reflection of the cavity as a function of the frequency and the power (2D plot).



    Hardware to be used:
        - R&S ZND VNA



    Before runnign the program:
    (Optionally) set the intended gate voltage manually


'''


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
title = 'A0_firstDevice_RevGatePol'
path = 'C:\\Users\\Localuser\\Documents\\DATA\\Hadi\\01_Lab Journals\\A_Nonlinearity in graphene resonators\\A0 2020-10-27 measurements'

gate_voltage = 0 # to be set manually
start_power = 0 #
stop_power = 9 
power_points = 300

monitor_ratio = 5 #shows 1 out of "monitor_ratio" spectrums
show_figure = False

start_freq = 2  # start grequency [MHz]
stop_freq = 50 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 1001 # frequency sweep points
IF_bandwidth= 1000


frequency_pattern = np.linspace(start_freq, stop_freq, freq_points)
power_pattern = np.linspace(start_power,stop_power, power_points)



# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False

prefix = title+'_PowerSweep'

font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }

colnames = ['Frequency (Hz)', 'S21re ()', 'S21im ()', 'S21dB (dB)', 'S21Ph (rad)', 'Power (dBm)', 'Time (s)', 'Gate Voltage (V)', 'S21 (uW)']
Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)

##########################################################
''' Initializing the devices '''


# initializing the ZND
VNA = RS_ZND('TCPIP::192.168.10.151::INSTR', reset=False)
VNA.SetSweepfrequency(start_freq, stop_freq, freq_points)
VNA.SetIFBW(IF_bandwidth) #Set IF bandwidth in Hz


#############################################################
''' measurements '''
# amping to the target  gate

S_amp_Watt = np.array([],[])
S_phase = np.array([],[])

STOP = False
            

t_in = time.time()


count = 0
for count, power in enumerate(power_pattern):
    if STOP:
        break
    VNA.SetPower(power) #[db] minimum -30db

    data = VNA.MeasureScreen_pd()
    amp_data = np.array(data['S21dB (dB)'])
    amp_data_Watt = 10**(amp_data/20)*1e6
    phase_data = np.array(data['S21Ph (rad)'])

    t = time.time() - t_in


    if count == 0:

        S_amp_Watt = amp_data_Watt
        S_phase = phase_data

    else:

        S_amp_Watt = np.array(np.vstack((S_amp_Watt,amp_data_Watt)))
        S_phase = np.array(np.vstack((S_phase,phase_data)))


        plt.rcParams["figure.figsize"] = [16,9]

        if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
            plt.subplot(2, 2, (1,3))
            plt.plot(data['Frequency (Hz)']*1e-6,amp_data_Watt)
            plt.ylabel('S11 (uW)')
            plt.xlim(np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6)
            plt.title(title + ' Gate: '+ str(gate_voltage) + ' V')



        plt.subplot(2, 2, (2,4))

        if count > 0:
            extent = [np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6, power_pattern[0], power_pattern[count]]
            plt.imshow(S_amp_Watt, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = np.min(np.min(S_amp_Watt)), vmax = np.max(np.max(S_amp_Watt)))



        plt.ylabel('Power (dBm)')
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
                print('s detected')
                print('--------------------------------')
                break



stlab.metagen.fromarrays(Data,frequency_pattern,power_pattern[0:count+1],xtitle='frequency (MHz)', ytitle='Power (dBm)',ztitle='',colnames=colnames)


#############################################################
''' output '''

if save_data:

    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
    Data.close()
    plt.close()

#############################################################
''' finishing '''

print('FINISHED')
