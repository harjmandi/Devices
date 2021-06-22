''' This program uses R&S ZNB VNA to detect the resonace of a microwave cavity.
The program eventually plots the reflection of the cavity as a function of the frequency and time (2D plot) to probe the reproducibility of the measurements.



    Hardware to be used:
        - R&S ZND VNA


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

def SetRemote (gate_device):
    gate_device.write("SYSTEM:REMOTE")

def SetLocal (gate_device):
    gate_device.write("SYSTEM:LOCAL")

def SetVoltage(gate_device, Vol):
    mystr = numtostr(Vol)
    mystr = ':SOUR:VOLT:LEV ' + mystr
    gate_device.write(mystr)
    # gate_dev.write(":SOUR:VOLT:LEV 2.8")

def GetVoltage(gate_device):  
        volt = gate_device.query("MEAS:VOLT?")
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
        num = gate_device.query("MEAS:CURR?")
        return float(num)

def TurnOn(gate_device):
    gate_device.write("OUTP:STAT:ALL 1")


def TurnOff(gate_device):
    gate_device.write("OUTP:STAT:ALL 0")

def Close(gate_device):
    gate_device.close()

def WhoIsIt(gate_device):
    gate_device.query("*IND?")

###############################################################################################
''' Definitions'''

#definitions
title = 'A32_offCavity2'
path = 'C:\\Users\\Hadi\\surfdrive\\01_Lab Journals\\A_Nonlinearity in graphene resonators\\A32 2021-02-16 measurements\\Day 1'

#time_step = 1#20 #time step between two subsequent measurements

monitor_ratio = 3 #shows 1 out of "monitor_ratio" spectrums
show_figure = True

start_freq = 1  # start grequency [MHz]
stop_freq = 15 # stop frequency [GHz] maximum 8.5GHZ for ZND
freq_points = 2001 # frequency sweep pointsgoogle
#IF bandwidth= 100, this is for my own records and does not affect the VNA settings.

power = 10 #sweep power [dB] range: -45 to 3 dB

frequency_pattern = np.linspace(start_freq, stop_freq, freq_points)


# output setting
save_data =True
pygame.init()
pygame.display.set_mode((100,100))
STOP = False

prefix = title+'_reproducibility'

font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }

colnames = ['Frequency (Hz)', 'S21re ()', 'S21im ()', 'S21dB (dB)', 'S21Ph (rad)', 'Power (dBm)', 'Time (s)', 'S21 (uW)']
Data = stlab.newfile(prefix,'_',colnames,autoindex = True, mypath= path)

##########################################################
''' Initializing the devices '''

# initializing the ZND
VNA = RS_ZND('TCPIP::192.168.10.151::INSTR', reset=False)
# VNA.SetSweepfrequency(start_freq, stop_freq, freq_points)
# VNA.SetPower(power) #[db] minimum -30db
# VNA.SetIFBW(1e3) #Set IF bandwidth in Hz
# VNA.SetSweepTime(SweepTime)

# VNA.AutoScale()
# # VNA.write('INST:SEL "NA"')  #set mode to Network Analyzer
# if measure == 'OnePort':z
#   VNA.SinglePort()
# elif measure == 'TwoPort':
#   VNA.TwoPort()



# if averaging > 1:
#   VNA.write('SENS:AVER:COUN %d' % averaging)
#   # VNA.write('SENS:AVER ON')
#   # VNA.write('SENS:AVER:CLEAR')


#############################################################
''' measurements '''

S_amp_Watt = np.array([],[])
S_phase = np.array([],[])
time_array = np.array([])


STOP = False
            

t_in = time.time()



count = 0
# while not STOP:
while count < 12:
    if STOP:
        break
    try:

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


            plt.rcParams["figure.figsize"] = [16,9]

            if (count-1)//monitor_ratio == (count-1)/monitor_ratio:
                plt.subplot(2, 2, (1,3))
                plt.plot(data['Frequency (Hz)']*1e-6,amp_data_Watt)
                plt.ylabel('S11 (uW)')
                plt.xlim(np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6)
                plt.title(title + ' Power: '+ str(power) + ' dBm')



            plt.subplot(2, 2, (2,4))

            if count > 0:
                extent = [np.min(data['Frequency (Hz)'])*1e-6,np.max(data['Frequency (Hz)'])*1e-6, 0, count]
                plt.imshow(S_amp_Watt, origin = 'lower', aspect='auto', extent=extent, cmap='seismic', vmin = np.min(np.min(S_amp_Watt)), vmax = np.max(np.max(S_amp_Watt)))



            plt.ylabel('#')
            plt.title('S11 (uW)')
            plt.xlabel('Frequency (MHz)')



        if show_figure:
            plt.pause(0.5)


        if save_data:

            data['Power (dBm)'] = VNA.GetPower()
            data['Time (s)'] = t
            data['S21 (uW)'] = amp_data_Watt

            stlab.savedict(Data, data)




        print('ELAPSED TIME: {:.2f} min'.format(t/60))



        for cnt in range(1000):
            for event in pygame.event.get(): # stopping if 's' pressed
                if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
                    STOP = True
                    break
                    print('--------------------------------')
                    print('s detected')
                    print('--------------------------------')

        count = count+1
    except:
        print ('############STOP#################')






stlab.metagen.fromarrays(Data,frequency_pattern,time_array[0:count+1],xtitle='frequency (MHz)', ytitle='time (s)',ztitle='',colnames=colnames)




#############################################################
''' output '''

if save_data:


    plt.savefig(os.path.dirname(Data.name)+'\\'+prefix)
    Data.close()
    plt.close()

#############################################################
''' finishing '''

print('FINISHED')
