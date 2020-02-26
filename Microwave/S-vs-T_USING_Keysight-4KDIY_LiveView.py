''' This program uses KEISIGHT FieldFox to detect the resonace of a microwave cavity and record the temperature during warming up the fridge.
The program eventually plots the reflection of the cavity as a function of the frequency and the temperature (2D plot).



    Hardware to be used:
        - KEISIGHT FieldFox VNA
        - Keysight B2961A: For gating (?optional)
        - Rigol: to power up the room-T amplifier (otional)



    Before runnign the programm:
        - Make sure that room temperature amplifier is well wired: mounted on port 2 of the KEISIGHT FieldFox and it is powered up with 15 V with Rigol

    Wiring:
        -   For the reflection measurements with the directional-coupler inside the fridge: Out put of the KEISIGHT FieldFox (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
            eventually connected to the Port 2 on KEISIGHT FieldFox (through the circulator and low-T amplifier) and "input" port to the resonator.

'''


import os
import numpy as np
import time
import stlab
import stlabutils
from stlab.devices.RS_ZND import RS_ZND
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import pygame, sys
from pygame.locals import *
from matplotlib import cm
from array import *
from stlab.devices.Cryocon_44C import Cryocon_44C


###############################################################################################
''' Definitions'''

#definitions

prefix = 'C26_D3_mapping1_'
path = 'D:\\measurement_data_4KDIY\\Hadi\\C26 2020-02-06 measurements/'

gate_voltage = 0
measure = 'OnePort' # 'OnePort' or 'TwoPort'
tdelay_measure = 1 #time between resonance measurements
tdelay_idle = 10 # time between temperature measurements

low_T = 3
hight_T = 18

# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False
monitor_ratio = 5 #shows 1 out of "monitor_ratio" spectrums
adjust_phase = False

font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }

##########################################################
''' Initializing the devices '''

if gate_voltage != 0:
    from stlab.devices.Keysight_B2901A import Keysight_B2901A
    gate_dev = Keysight_B2901A('TCPIP::192.168.1.63::INSTR')
    gate_dev.SetModeVoltage()
    gate_dev.SetOutputOn()
    gate_dev.SetComplianceCurrent(safe_gate_current)
    gate_dev.RampVoltage(gate_voltage,tt=5, steps = 20)


# initializing the ZND
# ZND = RS_ZND('TCPIP::192.168.1.149::INSTR', reset=False)
VNA = stlab.adi(addr='TCPIP::192.168.1.230::INSTR',reset=False) # this is FieldFox


# initializing temperature sensor
dev = Cryocon_44C('TCPIP::192.168.1.4::5000::SOCKET', reset=True)

#############################################################
''' measurements '''

# modulating the gate voltage
count = 0 # couter of step numbers

S21dB = np.array([],[])
S21Ph = np.array([],[])
Temp = np.array([])
Time = np.array([])

t0 = time.time()
t = 0
temperature = 300
tdelay = tdelay_measure

while (not STOP):

    tt = time.time()
    t=tt-t0
    temperature = dev.GetTemperature('B')
    print ('Temperature:', temperature)
    if  temperature > hight_T:
        STOP = True

    if low_T < temperature < hight_T:

        tdelay = tdelay_measure
        data = VNA.MeasureScreen_pd()
        if measure == 'OnePort':
            amp_data = np.array(data['S11dB (dB)'])
            phase_data = np.array(data['S11Ph (rad)'])

        elif measure == 'TwoPort':
            amp_data = np.array(data['S21dB (dB)'])
            phase_data = np.array(data['S21Ph (rad)'])

        data['Temperature (K)'] = temperature

        Temp = np.append(Temp,temperature)
        Time = np.append(Time,t)

        data['Time (s)'] = t


        if count == 0:

            S_amp = amp_data
            S_phase = phase_data


            if adjust_phase:
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
                adjusted_phase = phase_data

        else:

            S_amp = np.array(np.vstack((S_amp,amp_data)))
            S_phase = np.array(np.vstack((S_phase,adjusted_phase)))



            plt.rcParams["figure.figsize"] = [16,9]

            if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
                plt.subplot(3, 1, 1)
                plt.plot(data['Frequency (Hz)'],amp_data)
                plt.ylabel('S11dB (dB)')
                # plt.xlim(np.minimum(data['Frequency (Hz)']),np.maximum(data['Frequency (Hz)']))

                plt.subplot(3, 1, 2)
                plt.plot(data['Frequency (Hz)'],adjusted_phase*180/np.pi)
                plt.ylabel('Phase (°)')
                # plt.xlim(np.minimum(data['Frequency (Hz)']),np.maximum(data['Frequency (Hz)']))


            plt.subplot(3, 1, 3)
            plt.contourf(data['Frequency (Hz)'],Temp,S_amp)
            plt.ylabel('T (K)')




        plt.pause(0.1)


        if save_data:

            # temp = tempdev.GetTemperature()
            data['Power (dBm)'] = VNA.GetPower()
            data['Gate Voltage (V)'] = gate_voltage

            if count==0:
                Data = stlab.newfile(prefix,'_',data.keys(),autoindex = True, mypath= path)
            stlab.savedict(Data, data)



        count+=1

        for event in pygame.event.get(): # stopping if 's' pressed
            if event.type == QUIT: sys.exit()

            if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s" (slower measurement)
                tdelay *= 2
                print ('Delay between the meaurement steps raised to', tdelay)


            if event.type == KEYDOWN and event.dict['key'] == 102: # corresponding to character "f" (faster measurement)
                tdelay *= 0.5

                print ('Delay between the meaurement steps lowered to', tdelay)

            if event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to character "e" (end measurement)
                STOP = True

    time.sleep(tdelay)




print('FINISHED')

#############################################################
''' output '''

if save_data:

    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
    plt.close()

    plt.plot(Time,Temp)
    plt.ylabel('Temperature (K)')
    plt.xlabel('Time (s)')

    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix+'_Temp')
    Data.close()














