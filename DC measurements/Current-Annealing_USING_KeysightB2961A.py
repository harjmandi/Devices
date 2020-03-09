''' 
This script aims to clean graphene devices by current annealing: biasing with high (upto mA) currents

THIS SCRIPT NEEDS TO BE RUN USING A COMMAND TERMINAL (NOT INSIDE SUBLIME).

Devices to be used: 
    - Keysight B2961A: current source and monitor


Wiring: 
    - Connect the "Force/Low" terminal inthe front to the device (Adaptor box is needed)!
'''

import stlab
import numpy as np
from stlab.devices.He7Temperature import He7Temperature
import matplotlib.pyplot as plt
from time import time as time
import pygame, sys 
from pygame.locals import *
import winsound
import os
from matplotlib.font_manager import FontProperties as fontP
from stlab.devices.Keysight_B2961A import Keysight_B2961A


########################################################
''' definitions '''
# experimental paramters
max_current = 100e3 # [uA] maximum applied current of the device = 100mA
current_ramp_spead = 5 # [uA/s] maximum current modulation spead
current_step = 0.1 # [uA] current steps to ramp the current up and down
resistance = 5.6e3 #initial resistance of the device
compliance = 42 # [V]: compliance voltage
# output
save_data =True
last_n_points = 5 #plotting last n seconds in a subplot. 
prefix = 'F18_e7_CA_250mK_'
path = 'D:\\measurement_data\\Hadi\\F- Multiterminal graphene JJ\\F18 2020-03-04 measurements with LP filters/'

sample_name = ''

########################################################
'''' initializing the equipments '''

# initializing the Keysight B2961A
isource = Keysight_B2961A()
isource.SetModeCurrent() # sets the device to current mode
isource.SetComplianceVoltage(compliance) # sets the compliance voltage limit to 50V (Maximum). 
# isource.CurrRangeAuto(True)
isource.SetOutputOn()



# initializing the temperature reading 
# tempdev = He7Temperature(addr='192.168.1.249',verb=False)

########################################################
''' experiment'''
End = False # flag to show the end of the program (when the command e is input)
initiated = False # flag showing the first round of the experiment; the script remains idle untile a first command is detected.\
                # Two seperate 'initiated' and 'action' are required: 'initiated' flag flippes and remains True after the first entery\
                # to determind the starting point (strating time) of the experiment. 'Action' flage can flip True and False during the experiment, curresponding to the inputs. 

action = False # flag to change the current

pygame.init()
pygame.display.set_mode((100,100))
my_time = np.array ([])
my_resistance = np.array([])
my_current = np.array([])
my_power = np.array([])
input_energy = np.array([])
count = 0
destination_current = 0
current = 0
vmeasure_gain = []

if save_data:
    parameters = ['time (s)', 
            'resistance (ohm)',
            'current (uA)',
            'sum input energy (J)'
            'power (W)'
            'temperature (K)']

    my_file= stlab.newfile(prefix,'',autoindex=True,colnames=parameters, mypath= path)



print ('\n-------------------------------------------------------------------')
print ('How to start?' 
    '\n "s" : set destination current, currently at:', destination_current, 'uA'
    '\n "a": adjust current ramp spead, currently is:', current_ramp_spead, '[uA/s]'
    '\n "u": step up the current by: +', current_step, '[uA]'
    '\n "d": step down the current by: -', current_step, '[uA]'
    '\n "z": fast return to zero by 10x voltage ramp speed',
    '\n "t": go automatic',
    '\n "k": show keys',
    '\n "e": stop the experiment'
    )
ramp_zero = False
addup_energy = 0

while not End:
    for event in pygame.event.get():
        if event.type == QUIT: sys.exit()
                
        if event.type == KEYDOWN and event.dict['key'] == 115: # corresponding to character "s"
            try:
                I_final = float(input('input new destination current [uA]: '))

                if np.abs(I_final) < np.abs(max_current):
                    massage = 'ramping to the destination current'
                    action = True
                    initiated = True
                    ramp_current = True

                else:
                    massage = 'ERROR: the device can not apply currents larger than 100 [mA]'
                    action = False
                    ramp_current = False


            except ValueError:
                massage = 'Not a number'
                action = False
                ramp_current = False


        elif event.type == KEYDOWN and event.dict['key'] == 97: # corresponding to character "a"
            ramp_current = False
            action = False
            accept = 'n'
            while accept =='n':
                try:
                    new_current_ramp_spead = np.abs(float(input('input the new current ramp speed: [V/s] ')))
                
                    if np.abs(new_current_ramp_spead/current_ramp_spead) > 5:
                        print ('WARNING:  the new current ramp speed is: ', int(np.abs(new_current_ramp_spead/current_ramp_spead)), 'times larger')
                        accept = input ('do you accept that? y: Yes, n: No ')

                        if accept == 'y':
                            current_ramp_spead = new_current_ramp_spead
                            massage = 'new current ramp speed set!'
                            
                        else:
                            massage = 'input current ramp speed cancelled!'

                except ValueError:
                    massage = 'not a number, waiting for the new command'

        
        elif event.type == KEYDOWN and event.dict['key'] == 117: # corresponding to character "u"
            destination_current +=current_step
            ramp_current = False
            if np.abs(destination_current) < np.abs(max_current):
                initiated = True
                massage = 'stepping up the current'
                action = True

            else:
                massage = 'ERROR: the device can not apply currents larger than 100 [mA]'
                action = False

        elif event.type == KEYDOWN and event.dict['key'] == 100: # corresponding to character "d"
            destination_current -=current_step
            massage = 'steping down the current'
            initiated = True
            action = True
            ramp_current = False


        elif event.type == KEYDOWN and event.dict['key'] == 122: # corresponding to character "z"
            I_final = 100e-3
            current_ramp_spead = 30*current_ramp_spead
            massage = 'ramping the current down to zero'
            initiated = True
            action = True
            ramp_current = True
            ramp_zero = True



        elif event.type == KEYDOWN and event.dict['key'] == 116: # corresponding to character "t"
            massage = 'automatic process to be completed'
            ramp_current = False
            action = False
            # Automatic feature to be completed later

        
        elif event.type == KEYDOWN and event.dict['key'] == 101: # corresponding to character "e"
            massage = 'Finishing!'
            ramp_current = False
            End = True
            action = False

        elif event.type == KEYDOWN and event.dict['key'] == 107: # corresponding to character "k"
            print ('\n-------------------------------------------------------------------')
            print (
            '\n "s" : set destination current, currently at:', destination_current, 'uA'
            '\n "a": adjust current ramp spead, currently is:', current_ramp_spead, '[uA/s]'
            '\n "u": step up the current by: +', current_step, '[uA]'
            '\n "d": step down the current by: -', current_step, '[uA]'
            '\n "z": fast return to zero by 10x voltage ramp speed',
            '\n "t": go automatic',
            '\n "k": show keys',
            '\n "e": stop the experiment')

        elif event.type == KEYDOWN:
            massage = 'unknown entery, waiting for the command'
            action = False 
            ramp_current = False

                
    if not initiated:
        start_time = int(time())
    else:
        
        print (massage)
        if action:
            
            if ramp_current:
                I0 = np.abs(isource.GetCurrent())/1e-6
                if np.abs(I_final -I0) < current_ramp_spead:
                    destination_current = I_final
                    ramp_current = False
                    massage ='Target current reached'
                    if ramp_zero:
                        ramp_zero = False
                        current_ramp_spead = 0.1*current_ramp_spead
                    
                else:
                    destination_current = I0 +np.sign(I_final-I0)*current_ramp_spead

            print ('current_ramp_spead',current_ramp_spead)
            print ('I0', I0)
            print('np.sign(I_final-I0)',np.sign(I_final-I0))
            print ('new set current is', destination_current, '[uA].')


            isource.SetCurrent(destination_current*1e-6)
            voltage = isource.GetVoltage()
            
            if voltage > compliance: # check for overload
                print ('COMPLIANCE LIMIT')
                winsound.Beep(440, 1000)
                isource.RampCurrent(current*1e-6,1e-3) # the current returns back to the last current setting before overloading
            else:
                print ('current set!')

        
        current = np.abs(destination_current)
        vm = isource.GetVoltage()
        power = vm*current*1e-6

       
        t = time()-start_time
        my_time = np.append (my_time,t)
        my_resistance = np.append (my_resistance,resistance)
        my_current = np.append(my_current,current)
        my_power = np.append(my_power,power)
        
        addup_energy += vm*current*1e-6*(my_time[count]-my_time[count-1])
        
      
        plt.rcParams["figure.figsize"] = [10,20]#[16,9]
        plt.suptitle(massage, fontsize=10, fontweight='bold')

        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(my_time,my_resistance/1000, '--r',marker='o')
        ax1.set_ylabel(r'Resistance (k$\Omega$)')
        ax1.set_xlabel('time (s)')
        ax1.legend(['resistance'], loc='upper left')

        ax2 = ax1.twinx()
        ax2.plot(my_time,my_current, '--b',marker='+', label="current")
        ax2.set_ylabel(r'Current ($\mu$A)')
        ax2.legend(['current'], loc='upper right')

        plt.text(0.13, 0.91, 'resistance: '+"{:3.1f}".format(resistance/1000)+r'$k\Omega$', fontsize=10, transform=plt.gcf().transFigure)
        plt.text(0.79, 0.91, 'current: '+"{:3.1f}".format(current)+r'$\mu A$', fontsize=10, transform=plt.gcf().transFigure)
        plt.text(0.4, 0.91, 'total heating energy: '+"{:4.3f}".format(addup_energy*1000)+'mJ', fontsize=10, transform=plt.gcf().transFigure)
        plt.text(0.4, 0.93, 'max. applied power: '+"{:4.3f}".format(max(my_power)*1000)+'mW', fontsize=10, transform=plt.gcf().transFigure)



        ax3= plt.subplot(2, 1, 2)
        ax4 = ax3.twinx()

        
        if count > last_n_points:

            sub_current = my_current[count-last_n_points:count]
            sub_resistance = my_resistance[count-last_n_points:count]/1000
            sub_time = my_time[count-last_n_points:count]
            
            ax3.plot(sub_time,sub_resistance, '--r', marker='o')
            ax4.plot(sub_time,sub_current, '--b', marker='+')
            ax3.set_xlim(min(sub_time), 1+max(sub_time))
            ax3.set_ylim(0.95*min(sub_resistance), 1.01*max(sub_resistance))

        else:
            ax3.plot(my_time,my_resistance/1000, '--r', marker='o')
            ax4.plot(my_time,my_current, '--b', marker='+')

  
        ax3.set_ylabel(r'Resistance (k$\Omega$)')
        ax3.set_xlabel('time (s)')
        ax3.legend(['resistance'], loc='upper left')
        ax4.set_ylabel(r'Current ($\mu$A)')
        ax4.legend(['current'], loc='upper right')
        

        if save_data:
            # line = [t,resistance, current, addup_energy, power, tempdev.GetTemperature()]
            line = [t,resistance, current, addup_energy, power]
            stlab.writeline(my_file,line)
        
        if current != 0:
            resistance = vm/(current*1e-6)
        elif count > 0:
            resistance = my_resistance[count-1]

        plt.pause(1)
        count+=1

isource.RampCurrent(0)
isource.SetOutputOff()
isource.close()

###############################################################################
''' saving the data '''

if save_data:
    
    plt.savefig(os.path.dirname(my_file.name)+'\\'+prefix) # saving figure
    my_file.close()



else: 
    plt.show()


'''

"s" : set destination current, currently at:', destination_current, 'uA'
"a": adjust current ramp spead, currently is:', current_ramp_spead, '[uA/s]'
"u": step up the current by: +', current_step, '[uA]'
"d": step down the current by: -', current_step, '[uA]'
"z": fast return to zero by 10x voltage ramp speed',
"t": go automatic',
"e": stop the experiment'

'''
