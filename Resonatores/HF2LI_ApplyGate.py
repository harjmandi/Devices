
from __future__ import print_function
import time
import numpy as np
import zhinst.utils
import sys


def gate_it(device_id, gate, out_channel, device, daq, out_mixer_channel, out_range = 10, frequency = 0.1, amplitude =77e-6, initialize = False):
	osc_index = 0
	out_channel-=1
	out_range_list = [10e-3,100e-3,1,10]

	if out_range not in out_range_list:
		print('### Unknonw output range for HF2LI ###')
		print('out range = ', out_range)
		sys.exit()
	

	if initialize:

		exp_setting = [['/%s/oscs/%d/freq'             % (device, osc_index), frequency],
					   ['/%s/sigouts/%d/add'         % (device, out_channel), 1],
					   ['/%s/sigouts/%d/on'            % (device, out_channel), 1],
					   ['/%s/sigouts/%d/enables/%d'    % (device, out_channel, out_mixer_channel), 1],
					   ['/%s/sigouts/%d/range'         % (device, out_channel), out_range],
					   ['/%s/sigouts/%d/amplitudes/%d' % (device, out_channel, out_mixer_channel), amplitude/out_range],
					   ['/%s/sigouts/%d/offset' % (device, out_channel), gate/out_range]]

	else:


		exp_setting = [['/%s/sigouts/%d/offset' % (device, out_channel), gate/out_range]]


	daq.set(exp_setting)