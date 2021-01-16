#!/usr/bin/python3

'''

Copyright 2020-2021 Guilhem Tiennot

Program that analyzes audio data from built-in microphone with FFT,
to measure speed of french emergency vehicles.

Dependencies: numpy, struct, math, time, threading, scipy, py-gnuplot,
	gtk+3, pyaudio

This file is part of sirène.py.

Sirène.py is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Sirène.py is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sirène.py.  If not, see <https://www.gnu.org/licenses/>.

'''

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

import numpy
import struct
import math
import threading
from scipy.signal import find_peaks
from customaudio import CustomAudio
from pygnuplot import gnuplot

# config vars

siren_freq=435			# Base frequency used to compute speed (in Hz)
rate=44100				# Audio sample rate (in Hz)
sound_chunk=1			# Duration of an audio chunk (in second)

min_speed_freq=405		# Min and max frequencies to compute the speed
max_speed_freq=465		# (otherwise it's considered as outliers)

min_fft_freq=350		# Min and max frequencies of the peaks given by FFT
max_fft_freq=550

peak_distance=60		# Minimal distance between peaks given by FFT (in samples)
peak_threshold=500000	# Minimal size of the peaks compared to neighboring samples
peak_height=500000		# Minimal size of the peaks given by FFT
sound_speed=330			# Speed sound in the air
freq_deviation=5		# Maximal distance to the last found frequency,
						# to avoid outliers (in Hz)

# end of config vars

previous_freq=0			

stop_thread=False
speed_label_markup="<span font_desc='DejaVu Sans Bold 150' color='#000088'>%s km/h</span>"

win = Gtk.Window()
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
speed_label = Gtk.Label()

def get_peaks(data):
	peaks = numpy.array([])
	coeffs = numpy.array([])
	w = numpy.fft.fft(data)
	freqs = numpy.fft.fftfreq(len(w), d=1/rate)
	
	between = (freqs > min_fft_freq) * (freqs < max_fft_freq)
	indexes = numpy.where(between)
	freqs = freqs[indexes]
	w = w[indexes]	
	
	# Save coeffs and frequencies, to plot them later
	with open("fft.csv", "w") as f:
		for i in range(len(w)):
			f.write("%d;%d\n" % (freqs[i], abs(w[i])))
		f.close()

	res = find_peaks(abs(w), distance=peak_distance, threshold=peak_threshold, height=peak_height)
	
	# some filtering
	for i in res[0]:
		if freqs[i] > min_speed_freq and freqs[i] < max_speed_freq:
			peaks = numpy.append(peaks, freqs[i])
			coeffs = numpy.append(coeffs, w[i])
	return peaks, coeffs

def get_speed(freq):
	# See wikipedia for the Doppler effect formula
	return (1-(siren_freq/freq))*sound_speed*3.6

def print_label(text):
	global speed_label
	global speed_label_markup
	global g
	global previous_freq
	
	# draw a line for the previous frequency (if any)
	g.cmd("unset arrow 2")
	if previous_freq != 0:
		g.cmd("set arrow 2 from %d,0 to %d,10000000 nohead" % (previous_freq, previous_freq))
	
	# Plot data and update label
	g.cmd("plot 'fft.csv' using 1:2 '%lf;%lf' with lines smooth mcsplines ls 1 notitle")
	speed_label.set_markup(speed_label_markup % text)
	
	# return False to avoid any risks of looping
	return False

def speed_loop():
	global stop_thread
	global sound_chunk
	global previous_freq
	global freq_deviation
	
	while not stop_thread:
		audio = a.rec(duration=sound_chunk)
		freqs, coeffs = get_peaks(audio)
		
		''' Algorithm to find peak :
			if we previously found found a frequency:
			  - search the nearest peak in frequency, and get it if it's close enough
			  - else get the greatest peak in value, if it's still close enough
			  - else give up (it means that we lost the signal)
			else get the greatest peak.
			
			idx_f is the list of frequency peaks,
			idx_c is the list of related coefficients.
			Last, idx is the most 
		
		'''
		
		idx = None
		if len(freqs) >= 1:
			idx_c = numpy.where(coeffs == numpy.amax(coeffs))[0][0]
			
			# if we previously found a frequency
			if previous_freq != 0:
				idx_f = (numpy.abs(freqs-previous_freq)).argmin()
				if abs(freqs[idx_f]-previous_freq) < freq_deviation:
					idx = idx_f
					previous_freq = freqs[idx]
				elif abs(freqs[idx_c]-previous_freq) < freq_deviation:
					idx = idx_c
					previous_freq = freqs[idx]
				else:
					previous_freq = 0
			# else get the greatest peak
			else:
				idx = idx_c
				previous_freq = freqs[idx]
		
		if len(freqs) > 0:
			idx=0
		# If we found some peak, display the speed.
		# But as we are in a thread, we cannot call any GTK+ functions.
		# So, add a callback in the glib event loop.
		if idx is not None:
			speed = round(get_speed(freqs[idx]))
			GLib.idle_add(print_label, speed)
		else:
			GLib.idle_add(print_label, "--")
			
			


a = CustomAudio(rate)
g = gnuplot.Gnuplot()
g.cmd('set terminal wxt font "arial,10" fontscale 1.0 size 1000, 500')
g.cmd('set style line 1 lw 3 lc "web-blue"')
g.cmd('set yrange [0:6000000]')
g.cmd('set title "FFT" ')
g.cmd('set title  font ",20" norotate')

# draw a line for the minimal height of peaks
g.cmd("set arrow 1 from graph 0,first %d to graph 1,first %d nohead" % (peak_height, peak_height))

thread = threading.Thread(target=speed_loop)
thread.start()

box.pack_start(speed_label, True, True, 20)

win.add(box)
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

stop_thread = True
