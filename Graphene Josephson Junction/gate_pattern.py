import numpy as np


def gate_pattern(target_gate=10, mode='double', data_points=100, shift_voltage=0):

	target_gate = np.abs(target_gate)
	if mode == 'double':
		data_points = np.round (data_points/4)

		gate_pattern_1 = np.linspace(0,target_gate,data_points) 
		gate_pattern_2 = np.linspace(target_gate,-target_gate,2*data_points)
		gate_pattern_3 = np.linspace(-target_gate,0,data_points)

		ramp_pattern = np.concatenate((gate_pattern_1, gate_pattern_2,gate_pattern_3), axis=None)+shift_voltage
		return_pattern = []
		error=False
		

	elif mode == 'single':
		data_points = np.round (data_points/2)

		gate_pattern_1 = np.linspace(-target_gate,target_gate,data_points) 
		gate_pattern_2 = np.linspace(target_gate,-target_gate,data_points)
		

		ramp_pattern = np.concatenate((gate_pattern_1, gate_pattern_2), axis=None)
		return_pattern = np.linspace(-target_gate,0,data_points/2)
		error=False
		
	else:
		print('mode is not known')

		ramp_pattern = []
		return_pattern = []
		error=True


	pattern = {'ramp_pattern':ramp_pattern, 'return_pattern':return_pattern, 'error':error}
	
	return pattern