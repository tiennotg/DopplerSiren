'''
Copyright 2020-2021 Guilhem Tiennot

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


import pyaudio
import struct
from time import time as time

CHUNK=512
FORMAT=pyaudio.paInt16
CHANNELS=1
RATE=16000
MIN_DURATION=1

class CustomAudio():
    def __init__(self, samplerate=RATE):
        self._p = pyaudio.PyAudio()
        self._s = self._p.open(format=FORMAT, channels=CHANNELS, rate=samplerate, input=True, output=False, frames_per_buffer=CHUNK)

    # if duration=0, records until average audio level drops below the threshold
    def rec(self, duration=0, threshold=1024):
        start_time = time()
        stop = False
        frames = []
        self._s.start_stream()
        
        while (not stop):
            data = self._s.read(CHUNK)
            data = struct.unpack('{n}h'.format(n=CHUNK), data) # Audio format is paInt16, so we expect n unsigned long, little endian
            frames = frames + list(data)
            data_max = max(data)
            if (duration == 0 and time()-start_time > MIN_DURATION and data_max < threshold) or (duration > 0 and time()-start_time > duration):
                stop = True
        self._s.stop_stream()
        return frames
    
    def __del__(self):
        self._p.terminate()
    
