
from __future__ import print_function
import time
import numpy as np
import zhinst.utils


def R_measure(device_id, amplitude, out_channel, in_channel, time_constant, frequency, poll_length, device, daq, out_mixer_channel, bias_resistor, in_range, out_range, diff, calibration_factor = 1.45, add = False, offset =0, ac = False):
	"""Run the example: Connect to the device specified by device_id and obtain
	demodulator data using ziDAQServer's blocking (synchronous) poll() command.

	Returns:
	  sample (dict of numpy arrays): The demodulator sample dictionary with the
		additional demod R and demod phi fields calculated in the example.

	Raises:
	  RuntimeError: If the device is not "discoverable" from the API.
	"""
	
	''' Initial definitions'''
  


	demod_index = 0
	osc_index = 0
	demod_rate = 1e3
	in_channel-=1
	out_channel-=1
	out_range_list = [10e-3,100e-3,1,10]

	if out_range not in out_range_list:
		print('### Unknonw output range for HF2LI ###')
	else:

		exp_setting = [['/%s/sigins/%d/ac'             % (device, in_channel), ac],
					   ['/%s/sigins/%d/range'          % (device, in_channel), in_range],
					   ['/%s/sigins/%d/diff'          % (device, in_channel), diff],


					   ['/%s/demods/%d/enable'         % (device, demod_index), 1],
					   ['/%s/demods/%d/rate'           % (device, demod_index), demod_rate],
					   ['/%s/demods/%d/adcselect'      % (device, demod_index), in_channel],
					   ['/%s/demods/%d/order'          % (device, demod_index), 4],
					   ['/%s/demods/%d/timeconstant'   % (device, demod_index), time_constant],
					   ['/%s/demods/%d/oscselect'      % (device, demod_index), osc_index],
					   ['/%s/demods/%d/harmonic'       % (device, demod_index), 1],

					   ['/%s/oscs/%d/freq'             % (device, osc_index), frequency],

					   ['/%s/sigouts/%d/add'         % ('dev352', 0), add],
					   ['/%s/sigouts/%d/on'            % (device, out_channel), 1],
					   ['/%s/sigouts/%d/enables/%d'    % (device, out_channel, out_mixer_channel), 1],
					   ['/%s/sigouts/%d/range'         % (device, out_channel), out_range],
					   ['/%s/sigouts/%d/amplitudes/%d' % (device, out_channel, out_mixer_channel), amplitude/out_range],
					   ['/%s/sigouts/%d/offset' % (device, out_channel), offset/out_range]]

		daq.set(exp_setting)

		# Unsubscribe any streaming data.
		daq.unsubscribe('*')

		# Wait for the demodulator filter to settle.
		time.sleep(10*time_constant)

		# Perform a global synchronisation between the device and the data server:
		# Ensure that 1. the settings have taken effect on the device before issuing
		# the poll() command and 2. clear the API's data buffers. Note: the sync()
		# must be issued after waiting for the demodulator filter to settle above.
		daq.sync()

		# Subscribe to the demodulator's sample node path.
		path = '/%s/demods/%d/sample' % (device, demod_index)
		daq.subscribe(path)

		# Sleep for demonstration purposes: Allow data to accumulate in the data
		# server's buffers for one second: poll() will not only return the data
		# accumulated during the specified poll_length, but also for data
		# accumulated since the subscribe() or the previous poll.
		#sleep_length = 1.0
		
		# For demonstration only: We could, for example, be processing the data
		# returned from a previous poll().
		#time.sleep(sleep_length)

		# Poll the subscribed data from the data server. Poll will block and record
		# for poll_length seconds.
		
		poll_timeout = 500  # [ms]
		poll_flags = 0
		poll_return_flat_dict = True
		data = daq.poll(poll_length, poll_timeout, poll_flags, poll_return_flat_dict)

		# Unsubscribe from all paths.
		daq.unsubscribe('*')

		# Check the dictionary returned is non-empty
		assert data, "poll() returned an empty data dictionary, did you subscribe to any paths?"

		# The data returned is a dictionary of dictionaries that reflects the node's path.
		# Note, the data could be empty if no data had arrived, e.g., if the demods
		# were disabled or had demodulator rate 0.
		assert path in data, "The data dictionary returned by poll has no key `%s`." % path

		# Access the demodulator sample using the node's path.
		sample = data[path]

		# Let's check how many seconds of demodulator data were returned by poll.
		# First, get the sampling rate of the device's ADCs, the device clockbase...
		clockbase = float(daq.getInt('/%s/clockbase' % device))
		# ... and use it to convert sample timestamp ticks to seconds:
		dt_seconds = (sample['timestamp'][-1] - sample['timestamp'][0])/clockbase
		print("poll() returned {:.3f} seconds of demodulator data.".format(dt_seconds))
		
		tol_percent = 50
		
		assert (dt_seconds - poll_length)/poll_length*100 < tol_percent, \
			"Duration of demod data returned by poll() (%.3f s) differs " % dt_seconds + \
			"from the expected duration (%.3f s) by more than %0.2f %%." % \
			(poll_length, tol_percent)


		measured_R = calibration_factor*np.mean(sample['x'])*bias_resistor/amplitude
		measured_X = np.mean(np.abs(sample['x'] + 1j*sample['y']))*bias_resistor/amplitude
		measured_phi = np.mean(np.angle(sample['x'] + 1j*sample['y']))
		
		measured_duration = dt_seconds
		
		#measured = {'resistance':measured_R, 'angle':measured_phi, 'duration':measured_duration}
		measured = [measured_R, measured_X, measured_phi, measured_duration]

		return measured
