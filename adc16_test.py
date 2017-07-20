import numpy as np
import numbers
import matplotlib.pyplot as plt
import random

# Before running the testing methods, please prepare the parameter "snap" with the recipe below:
# Apply modification on line 171 of https://github.com/ianmalcolm/mlib_devel/commit/6a48ef8289672364836598f385378a3338817f3b#diff-e9c4a7eb227bd864f7d96900f1813164R171
# Download https://github.com/domagalski/roach-adc-tutorial/blob/master/fpga/snap_adc.slx and build it
# With a SNAP+RPI platform, download bitstream and run following code:
# import ......
# fpga=corr.katcp_wrapper.FpgaClient('10.1.0.23')
# fpga.progdev('snap_adc_2017-07-19_1136.bof')
# snap=adc16.SNAPADC(fpga)

# These test methods work on https://github.com/ianmalcolm/mlib_devel/tree/high_resolution_adc as well

def clockAlignmentTest(snap,freqs=None):
	""" Stress test on line clock and frame clock alignment

	Make an instance of SNAPADC and pass it along with a list of frequencies to this method

	The return of this method "stats" is a 2-column numpy array. The 1st column is the
	frequency and the 2nd column indicates success of failure. 0 means a complete success.
	
	SUCCESS = 0
	ERROR_LMX = 1
	ERROR_MMCM = 2
	ERROR_LINE = 3
	ERROR_FRAME = 4
	ERROR_RAMP = 5

	"""

	# Supported frequency range: 60MHz ~ 1000MHz
	# Currently each test case takes approximatly 20 seconds, involving following actions
	## configuring frequency synthesizer LMX2581
	## configuring clock source switch HMC922
	## configuring ADCs HMCAD1511 (support HMCAD1520 in future)
	## configuring IDELAYE2 and ISERDESE2 inside of FPGA
	## Testing under dual pattern and ramp mode

	if freqs==None:
		freqs = range(60, 1001, 10)	# integer frequencies
		for i in range(1000):
			freqs += [random.randint(60000,1000000)/1000.0] # fractional frequencies

	stats = np.empty((0,2))

	# check parameters
	if not isinstance(freqs,list):
		raise ValueError("Invalid parameter")
	elif not all(isinstance(freq,numbers.Number) for freq in freqs):
		raise ValueError("Invalid parameter")
	elif not all(freq>=60 and freq<=1000 for freq in freqs):
		raise ValueError("Invalid parameter")

	for freq in freqs:
		if freq >= 60 and freq <= 250:
			nChannel = 4
		elif freq <= 500:
			nChannel = 2
		elif freq <= 1000:
			nChannel = 1
		else:
			continue

		print("Testing frequency {0} and nChannel {1}".format(freq,nChannel))

		ret =  snap.init(freq,nChannel)

		if ret != snap.SUCCESS:
			print("Failed on {0}".format(freq))

		stats = np.append(stats,np.array([[freq,ret]]),axis=0)

		# Shuffle settings so that next test case starts with an incorrect frame clock
		# alignment
		snap.bitslip()

	return stats

def rampTest(snap):
	""" Do a ramp test

	Run this test after properly initialising SNAPADC, i.e. snap.init()
	"""

	# The quick way
	errs = snap.testPatterns(taps=None,mode='ramp')
	# if not np.all(np.array([adc.values() for adc in errs.values()])==0):
	# 	return self.ERROR_RAMP
	# Results should be all zeros
	print(errs)

	# Or a manual way, and perform a visual check
	snap.adc.test('en_ramp')
	snap.snapshot()
	snap.adc.test('off')	# optional
	r=snap.readRAM()
	print(r)

def realSignal(snap):
	""" Collect some real signal under different settings

	"""

	print("Collecting signals from all ADCs with the same settings")
	snap.init(250,4)
	snap.adc.selectInput([1,2,3,4])
	snap.snapshot()
	r=snap.readRAM()


	print("Collecting signals from all ADCs, having different input selections")
	# Use with caution, not fully tested
	snap.init(500,2)
	snap.selectADC(0)		# Select ADC0
	snap.adc.selectInput([1,1,3,3])
	snap.selectADC([1,2])		# Select ADC1 and ADC2
	snap.adc.selectInput([2,2,4,4])

	snap.snapshot()
	r=snap.readRAM()


#	# Use with caution, not fully tested
#	print("Collecting signals from all ADCs, having different operating mode")
#	snap.init(250,4)	# init
#
#	snap.selectADC(0)	# Select ADC0
#	snap.adc.setOperatingMode(4)	# Enter into 4 channel mode
#	print("\tAligning clock of ADC0")	# The clock aligning is only performed on ADC0
#	if snap.alignLineClock():
#		if snap.alignFrameClock():
#			snap.adc.selectInput([1,2,3,4])
#
#	snap.selectADC(1)
#	snap.adc.setOperatingMode(2)
#	print("\tAligning clock of ADC1")
#	if snap.alignLineClock():
#		if snap.alignFrameClock():
#			snap.adc.selectInput([2,2,3,3])
#
#	snap.selectADC(2)
#	snap.adc.setOperatingMode(1)
#	print("\tAligning clock of ADC2")
#	if snap.alignLineClock():
#		if snap.alignFrameClock():
#			snap.adc.selectInput([2,2,2,2])
#		
#	snap.selectADC()	# optional: Select all ADCs
#	snap.snapshot()
#	r=snap.readRAM()

def plot(snap,data,mode,resolution=8,impedance=50):
	""" Plot a snapshot in dbm
	"""

	data = snap.adc.interleave(data,mode)

	stride = 2.0 / (2**(resolution)-1)
	data = data * stride - 1;				# Voltage
	data = 10 * np.log10((data ** 2) / impedance * 1000)	# dbm

	label = ['channel'+str(i) for i in range(1,data.shape[1]+1)]
	t = range(data.shape[0])
	hplt = plt.plot(t,data)
	plt.legend(hplt,label)
	plt.xlabel('Time')
	plt.ylabel('Power (dbm)')
	plt.show()


def freqSyntTest(lmx,freqs=None):
	""" Sweep frequency from 60MHz to 1000MHz

	Return failed frequencies
	"""

	# lmx = LMX2581(fpga,'lmx_ctrl')

	lmx.init()

	stats = np.empty((0,1))

	if freqs==None:
		freqs = range(60, 1001)		# integer frequencies
		for i in range(1000):
			freqs += [random.randint(60000,1000000)/1000.0] # fractional frequencies

	# check parameters
	if not isinstance(freqs,list):
		raise ValueError("Invalid parameter")
	elif not all(isinstance(freq,numbers.Number) for freq in freqs):
		raise ValueError("Invalid parameter")
	elif not all(freq>=60 and freq<=1000 for freq in freqs):
		raise ValueError("Invalid parameter")

	for freq in freqs:
		print("Testing lmx on frequency {0}".format(freq))
		if not lmx.setFreq(freq):
			print("\tlmx failed on frequency {0}".format(freq))
			stats = np.append(stats,[freq])

	return stats
