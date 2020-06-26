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
import matplotlib.pyplot as plt
import pygame, sys
from pygame.locals import *
from array import *
from stlab.devices.Cryocon_44C import Cryocon_44C
from stlab.devices.RS_ZND import RS_ZND


###############################################################################################
''' Definitions'''

#definitions

prefix = 'C26_UL_TempSweep_'
title = 'Vg = 0V, Power = +3dBm'
path = 'D:\\measurement_data_4KDIY\\Hadi\\C26 2020-05-29 measurements'

gate_voltage = 0 #This is not correct: I set the voltage directly on the SMU.
measure = 'TwoPort' # 'OnePort' or 'TwoPort'
tdelay_measure = 0.1 #time between resonance measurements
tdelay_idle = 0.1 # time between temperature measurements

''' EXTRA paramters (set manually on the VNA)
start frequency: 4.8433 GHz
stop frequency: 5.1128 GHz
resolution: 201 points
IF bandwidth: 100 Hz
power: 3
no averaging
'''

low_T = 3.25
hight_T = 18

safe_gate_current = 5e-3 # [A], safe current leakage limit, above this limit S1h unit gives an error. With in this limit, the oxide resistance below 4MOhm at 10Vg (400KOhm at 1Vg)) to be considerred not leacky!


# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False
monitor_ratio = 3 #shows 1 out of "monitor_ratio" spectrums

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
VNA = RS_ZND('TCPIP::192.168.1.149::INSTR', reset=False)


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


        else:

            S_amp = np.array(np.vstack((S_amp,amp_data)))
            S_phase = np.array(np.vstack((S_phase,)))



            plt.rcParams["figure.figsize"] = [16,9]

            if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
                plt.subplot(3, 1, 1)
                plt.plot(data['Frequency (Hz)']*1e-9,amp_data)
                plt.ylabel('S11dB (dB)')
                plt.title(title)
                plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)


                plt.subplot(3, 1, 2)
                plt.plot(data['Frequency (Hz)']*1e-9,phase_data*180/np.pi)
                plt.ylabel('Phase (°)')
                plt.xlim(np.min(data['Frequency (Hz)'])*1e-9,np.max(data['Frequency (Hz)'])*1e-9)


            plt.subplot(3, 1, 3)
            plt.contourf(data['Frequency (Hz)'],Temp,S_amp)
            plt.ylabel('T (K)')
            plt.xlabel('Frequency (GHz)')





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


if gate_voltage != 0:
    gate_dev.RampVoltage(0,tt=5, steps = 20)
    gate_dev.close()













