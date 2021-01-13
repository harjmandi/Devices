''' This program uses R&S ZNB VNA to detect the resonace of a microwave cavity and TENMA to apply a gate voltage to a coupled graphene.
The program eventually plots the reflection of the cavity as a function of the frequency and the gate voltage (2D plot).



    Hardware to be used:
        - R&S ZND VNA
        - Keysight B2961A: For gating



    Before runnign the programm:

    Wiring:
        -   For the reflection measurements with the directional-coupler inside the fridge: Out put of the KEYSIGHT FieldFox (port 2) is connected to the side port "-20 dB" of the coupler, "output " port
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
import stlab
import stlabutils

from stlab.devices.RS_ZND import RS_ZND

# Functions NOTE: ideally this functions has to be intergrated into a TENMA class; but I did not manage to do that yet. so I put them here. 
def numtostr(mystr):
    return '%.2f' % mystr

def SetVoltage(gate_device, Vol):
    mystr = numtostr(Vol)
    mystr = 'VSET1:' + mystr
    print('mystr =', mystr)
    gate_device.write(mystr)

def GetVoltage(gate_device):  
        volt = gate_device.query('VOUT1?')
        return float(volt)

def RampVoltage(gate_device, mvoltage, tt=5., steps=100):  #To ramp voltage over 'tt' seconds from current DAC value.
    v0 = GetVoltage(gate_device)
    print('v0 =',v0)
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

def WhoIsIt(gate_device):
    gate_device.query("*IND?")

###############################################################################################
''' Definitions'''

#definitions
title = 'A0'
path = 'C:\\Users\\Localuser\\Documents\\DATA\\Hadi\\A\\A0 2020-09-18 measurements'

time_step = 1#20 #time step between each gate voltage steps, to stablize the gate
ramp_spead = 0.2 # the safe spead for ramping the gate voltage [V/s]
start_gate = 1 #
stop_gate = 0 


monitor_ratio = 10 #shows 1 out of "monitor_ratio" spectrums

start_freq = 4.7737  # start grequency [MHz]
stop_freq = 5.3889 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 1001 # frequency sweep points
#IF bandwidth= 1000, this is for my own records and does not affect the VNA settings.

power = -45 #sweep power [dB] range: -45 to 3 dB
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



##########################################################
''' Initializing the devices '''

# TENMA setting
rm = pyvisa.highlevel.ResourceManager() # Opens the resource manager and sets it to variable rm
gate_dev = rm.open_resource("ASRL8::INSTR", baud_rate = 9600, data_bits = 8)
gate_dev.write_termination = '\n'
gate_dev.read_termination = '\n'
gate_dev.send_end = True
gate_dev.StopBits = 1





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

S_amp = np.array([],[])
S_phase = np.array([],[])
time_array = np.array([])


STOP = True

print ('press "s" when reasy to start')
while STOP:
    for event in pygame.event.get(): # stopping if 's' pressed
        if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
            STOP = False
            

t_in = time.time()


count = 0
while STOP == False:
    SetVoltage(gate_dev, stop_gate)

    data = VNA.MeasureScreen_pd()
    amp_data = np.array(data['S21dB (dB)'])
    phase_data = np.array(data['S21Ph (rad)'])

    t = time.time() - t_in


    if count == 0:

        S_amp = amp_data
        S_phase = phase_data
        time_array = t

    else:

        S_amp = np.array(np.vstack((S_amp,amp_data)))
        S_phase = np.array(np.vstack((S_phase,phase_data)))
        time_array = np.append(time_array,t)


        plt.rcParams["figure.figsize"] = [16,9]

        if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
            plt.subplot(2, 2, 1)
            plt.plot(data['Frequency (Hz)']*1e-6,amp_data)
            plt.ylabel('S11dB (dB)')
            plt.xlim(np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6)
            plt.title(title + ' Power: '+ str(power) + ' dBm')

            plt.subplot(2, 2, 3)
            plt.plot(data['Frequency (Hz)']*1e-6,phase_data*180/np.pi)
            plt.ylabel('Phase (°)')
            plt.xlim(np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6)
            plt.xlabel('frequency (MHz)')



        plt.subplot(2, 2, (2,4))

        if count > 0:
            extent = [np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6, 0, t]
            plt.imshow(S_amp, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = -38, vmax = -22)



        plt.ylabel('$time$ (s)')
        plt.title('S11dB (dB)')
        plt.xlabel('Frequency (MHz)')



    plt.pause(0.5)


    if save_data:

        data['Power (dBm)'] = VNA.GetPower()
        data['Time (s)'] = t

        if count==0:
            colnames = ['Frequency (Hz)', 'S21re ()', 'S21im ()', 'S21dB (dB)', 'S21Ph (rad)', 'Power (dBm)', 'Time (s)']
            Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)

        stlab.savedict(Data, data)




    print('ELAPSED TIME: {:.2f} min'.format(t/60))

    count = count+1

    # for cnt in range(20):
    #     for event in pygame.event.get(): # stopping if 's' pressed
    #         if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
    #             break
    #             STOP == True
    #             print('--------------------------------')
    #             print('s detected')
    #             print('--------------------------------')

    # while not STOP:
    for cnt in range(1000):
        for event in pygame.event.get(): # stopping if 's' pressed
            if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
                STOP = True
                RampVoltage(gate_dev,0,tt=ramp_time) # to safely return back the gate voltage
                break
                print('--------------------------------')
                print('s detected')
                print('--------------------------------')



stlab.metagen.fromarrays(Data,frequency_pattern,time_array,xtitle='frequency (Hz)', ytitle='gate voltage (V)',ztitle='',colnames=colnames)

print('FINISHED')

#############################################################
''' output '''

if save_data:

    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
    Data.close()
    plt.close()

