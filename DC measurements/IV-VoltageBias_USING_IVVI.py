''' This program uses IVVI S1H to apply a gate voltage and S3b as a Voltage bias to measure the resistance of the sample


  Hardware to be used:
    - IVVI S1h: For gating
    - IVVI S3b: As the Voltage source
    - IVVI M1b: for current measurement
    - IVVI M0: convert current measurement into Voltage

    - Keithley 2000 or DMM6500:  to measure the voltage drop accross the sample
    - Keithley 2000 or DMM6500:  to measure the leakacge current




'''

##### NOTE: with the current version, the calibration does not work for small current (~nA) ##############

import stlab
import stlabutils
from stlab.devices.IVVI import IVVI_DAC
import numpy as np
import time
from pygame.locals import *
import pygame, sys
import matplotlib.pyplot as plt
import os
import sys




''' input '''
prefix = 'F20_IV_f1-1to2-floating34_VBias_IVVI'
path = 'D:/measurement_data_4KDIY/Hadi/F20 2020-05-30 measurements/'

T = 3.36 # Temperature

V_bias_max = 20e-6 # [V] Maximum bias Voltage, The bias voltage should be chosen considering the total resistance of the sample + source and measure units (normally < 3kOhm)
V_bias_min = -V_bias_max #[V], 100 uV at Dirac point (~1kOhm) corresponds to 100uV/(1+3 kOhms) = 25 nA.
V_bias_ofset = 0 #[V] offset
delta_V_bias = V_bias_max/5 # [V]

measure_average = 10 # number of the measurements per each bias Voltage for averaging
time_sleep_measure = 0.05 # slee time in between measurements
calibrate = True # Calibrate for the internal resistances of the measurement units

Vgmax = 1 # Maximum gate voltage [V]
Vgmin = -Vgmax # Minimum gate voltage [V]
deltaVg = 0.2 # Gate voltage steps [V]


gate_ramp_speed = 1 # Gate ramp speed [V/s], proposed: 0.5
time_sleep_gate = 5 #sleep time to stablize the gate [s], proposed: 5
measure_gate_leakage = True

# DACs
S1h_dac = 1 #DAC number for gate voltage
S3b_dac = 5  #DAC number for Voltage source

# gains
M1b_gain = 1e8  #V/A gain for current to voltage conversion, set on M1b unit
M1b_postgain_switch = 100#postgain switch [x100ac x1 x100dc], set on M1b unit
S3b_range = 100e-6  #Full range of the applied current, set on S4c
S1h_gain = 45. #V/V gain for the applied gate, set on S1h
M1b_mode = 'Low-Noise' # 'Low-Noise' or 'Low-Rin'


M1b_total_gain = M1b_gain*M1b_postgain_switch


''' Check for errors '''
EXIT = False
if V_bias_max+V_bias_ofset > S3b_range:
    print ('Maximum bias voltage exceeds the range on S3b.')
    EXIT = True

if Vgmax > 2*S1h_gain:
    print ('Maximum gate voltage exceeds the range on S1h.')
    EXIT = True

if EXIT:
    sys.exit(0)


''' Initialize '''

if calibrate:
    prefix += '_with-calib'
else:
    prefix += '_no-calib'

pygame.init()
pygame.display.set_mode((100,100))


## Output setting
idstring = '_at{:.2f}mK'.format(T).replace('.','p')
colnames = ['Vset (V)', 'Imeas (A)', 'R (Ohm)','Vgate (V)', 'T (mK)', 'Time (s)', 'Ileakage (nA)']
myfile = stlab.newfile(prefix, idstring, colnames, autoindex=True, mypath= path)


# Vglist = np.append(np.linspace(Vgmax, Vgmin, int((Vgmax-Vgmin)/deltaVg)+1),np.linspace(Vgmin, Vgmax, int((Vgmax-Vgmin)/deltaVg)+1))
Vglist = np.linspace(Vgmax, Vgmin, int((Vgmax-Vgmin)/deltaVg)+1)

if Vgmax == Vgmin:
    Vglist =[Vgmax]

Vg_ini = Vglist[0]

# V_bias_list = np.linspace(V_bias_max, V_bias_min, int((V_bias_max-V_bias_min)/delta_V_bias)+1)+V_bias_ofset
V_bias_list = np.linspace(V_bias_max, V_bias_min, int((V_bias_max-V_bias_min)/delta_V_bias)+1)+V_bias_ofset

END = False

if S3b_range >= 1e-3:
    coeff = 1e3
    unit = 'm'
else:
    coeff = 1e6
    unit = '$\mu$'

plt.rcParams["figure.figsize"] = [16,9]
palette = plt.get_cmap('Set1') # create a color palette


##Inititalizing the devices
ivvi = IVVI_DAC(addr='COM3', verb=True)
ivvi.RampAllZero(tt=2., steps = 20)

Imeas = stlab.adi(addr='TCPIP::192.168.1.105::INSTR') #for measuring the current converted to Voltage at M0 output

if Vgmax !=0 and measure_gate_leakage:
    v_gateleakage = stlab.adi(addr='TCPIP::192.168.1.106::INSTR') #for measuring the leakage current
else:
    I_leakage = -1

''' Start the measurement '''


## Calibration for internal resistors
overshoot = False

if M1b_mode == 'Low-Noise':
    R_exp = 2000+ M1b_gain*1e-3

if M1b_mode == 'Low-Rin':
    R_exp = 2000+ M1b_gain*1e-4

if calibrate:
    I_cal = []
    print('Calibration for internal resistances:')
    input('Please short the S3b output and M1b input, press ENTER to continue ...')


    for V_bias in V_bias_list:
        ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.1, steps = 5)
        i_cal = 0
        for cnt in range(measure_average):
            Iread = float(Imeas.query('READ?'))
            i_cal += Iread / M1b_total_gain
            time.sleep(time_sleep_measure)
        I_cal = np.append(I_cal,i_cal/measure_average)

    R_int = np.average(np.diff(V_bias_list)/np.diff(I_cal))
    print ('Calibration Finished: total internal resistance is {:.1f}kOhms.'.format(1e-3*R_int))
    print ('Expected internal resistance is {:.2f}kOhm'.format(1e-3*R_exp))

    h = input ('Connect to the device, press Enter to continue or "e" to exit.' )

    if h == "e":
        sys.exit(0)

else:
    R_int = R_exp

## Ramping up the gate to the first point
if Vgmax !=0:
    print('############# Initialize back-gate to',Vg_ini,'V #############')
    ivvi.RampVoltage(S1h_dac,Vg_ini/S1h_gain*1000.,tt=np.abs(Vg_ini)/gate_ramp_speed) ##ramping to the Vg_ini
    print('Wait {:.0f}s for back-gate satbility at {:.1f}V'.format(time_sleep_gate,Vg_ini))
    time.sleep(time_sleep_gate)
last_time = time.time()


## Sweeping the gate
r_max = 0

plt.subplot(2,1,1)
plt.plot(V_bias_list*coeff,(V_bias_list/R_int)*1e9, '--b', linewidth=0.3, alpha=0.8, label = 'R_int')
plt.legend()


for gate_count,Vg in enumerate(Vglist):

    ivvi.RampVoltage(S3b_dac, V_bias_list[0]/S3b_range*1e3,tt=0.1, steps = 20)  #ramping up to the first bias point

    if END:
          break

    if Vgmax !=0:
        ivvi.RampVoltage(S1h_dac,Vg/S1h_gain*1000.,tt=deltaVg/gate_ramp_speed, steps = 20) ##ramping this gate voltage
        print('Wait {:.0f}s for back-gate stability at {:.1f}'.format(time_sleep_gate, Vg))
        time.sleep(time_sleep_gate)

        if measure_gate_leakage:
            I_leakage = float(v_gateleakage.query('READ?'))*1e3 #the factor 1e3 is used to convert the current to [nA]
        else:
            I_leakage = -1

    current_array = []
    V_bias_array = []
    R_array = []


    ## Sweeping the bias voltage

    for count, V_bias in enumerate(V_bias_list):

        for event in pygame.event.get():
          if event.type == QUIT:sys.exit()
          elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to the letter 'e'
            END = True
            if np.abs(Vg) > 1:
                ivvi.RampVoltage(S1h_dac,0.,tt=30.)

        if END:
          break

        ivvi.RampVoltage(S3b_dac, V_bias/S3b_range*1e3,tt=0.1, steps = 5)  #biasing

        I_tot = 0
        for cnt in range(measure_average):
            Iread = float(Imeas.query('READ?'))
            if Iread > 4:
                overshoot = True
            I_tot += Iread / M1b_total_gain
            time.sleep(time_sleep_measure)

        I = I_tot/measure_average

        current_array = np.append(current_array,I)
        V_bias_array = np.append(V_bias_array,V_bias)
        R = V_bias/I - R_int
        R_array = np.append(R_array,R)


        if count > 0: r_max = np.max(R_array)

        current_time = time.time()
        line = [V_bias, I, R, Vg, T, current_time - last_time, I_leakage]
        stlab.writeline(myfile, line)

        if Vgmax == Vgmin:
            plt.subplot(2,1,1)
            plt.title(prefix)

            plt.plot(V_bias_array*coeff,current_array*1e9, '--r', marker='.', markersize = 0.5, linewidth=0.5, alpha=0.9, label='{:.0f}Vg'.format(Vg))
            plt.ylabel('current [nA]')
            plt.xlim(V_bias_min*coeff,V_bias_max*coeff)
            if count == 0:
                plt.legend()

            plt.subplot(2,1,2)
            if calibrate:
                plt.plot((V_bias_array[1:]+delta_V_bias/2)*coeff,1e-3*R, '--r', marker='.', markersize = 1, linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
            else:
                plt.plot((V_bias_array[1:]+delta_V_bias/2)*coeff,1e-3*(R-R_int), '--r', marker='.', markersize = 1, linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))

            plt.ylabel('$(dV/dI) - R_{int}$ [$k\Omega$]')
            plt.xlabel('bias Voltage ['+unit+'V]')
            plt.xlim(V_bias_min*coeff,V_bias_max*coeff)
            # plt.ylim(0,10)
            plt.title("internal resistance: {:.1f} [$k\Omega$]".format(1e-3*R_int))

            if overshoot:
                plt.title("overshoot!")
            plt.pause(0.1)


    myfile.write('\n')

    if END:
          break

    if (Vgmax != Vgmin) and (not END):
        plt.subplot(2,1,1)
        plt.title(prefix)
        plt.plot(V_bias_list*coeff,current_array*1e9+gate_count*0.2, '--', marker='.', color=palette(gate_count), markersize = 1, linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
        plt.legend()
        plt.ylabel('current [nA]')
        plt.xlim(V_bias_min*coeff,V_bias_max*coeff)

        plt.subplot(2,1,2)
        plt.plot((V_bias_array[1:]+delta_V_bias/2)*coeff,1e-3*R_array, color=palette(gate_count), marker='.', markersize = 1, linewidth=1, alpha=0.9, label='{:.0f}Vg'.format(Vg))
        plt.legend()
        # if calibrate:
        #     plt.ylim(0,1.1*r_max/1000)

        plt.ylabel('dV/dI [k$\Omega$]')
        # plt.ylim(1e-3*R_int-0.5,1e-3*R_int+1.5)

        plt.xlim(V_bias_min*coeff,V_bias_max*coeff)
        plt.xlabel('bias Voltage ['+unit+'V]')


        if not calibrate:
            plt.title("internal resistance: {:.1f} [$k\Omega$]".format(1e-3*R_int))

        if overshoot:
                plt.title("overshoot!")



        plt.pause(0.1)


stlab.metagen.fromarrays(myfile,V_bias_list,Vglist[0:gate_count+1],zarray=[],xtitle='bias current (A)',ytitle='gate Voltage (V)',ztitle='',colnames=colnames)
plt.savefig(os.path.dirname(myfile.name)+'\\'+prefix)
if Vgmax !=0 and (not END):
    ivvi.RampVoltage(S1h_dac,0.,tt=60.)
ivvi.RampAllZero(tt=5.)
Imeas.close()
ivvi.close()

if Vgmax !=0 and measure_gate_leakage:
    v_gateleakage.close()

myfile.close()
