#!/usr/bin/env python3
"""
Created on Fri Dec 12 15:13:28 2025

@author: rld
"""

import time

import numpy as np
import pyaudio

DEVICE_INDEX = 0
# --- Configuration ---
VOLUME = 0.125  # range [0.0, 1.0]
SAMPLING_RATE = 44100  # sampling rate, Hz
DURATION = 1.0  # in seconds, can be a float
FREQUENCY = 750.0  # sine frequency, Hz, can be a float

# --- Generate samples ---
# Calculate the sample array for the sine wave
samples = (
    np.sin(2 * np.pi * np.arange(SAMPLING_RATE * DURATION) * FREQUENCY / SAMPLING_RATE)
).astype(np.float32)

# Convert the float32 array to a bytes sequence and apply volume
output_bytes = (VOLUME * samples).tobytes()

# --- Play sound ---
p = pyaudio.PyAudio()

device_count = p.get_device_count()
print(f"Total number of devices: {device_count}\n")

for i in range(device_count):
    device_info = p.get_device_info_by_index(i)
    print(f"Device Index: {i}")
    print(f"  Name: {device_info['name']}")
    print(f"  Max Input Channels: {device_info['maxInputChannels']}")
    print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
    print("-" * 20)


stream = p.open(
    format=pyaudio.paFloat32,
    channels=1,
    rate=SAMPLING_RATE,
    output=True,
    input_device_index=DEVICE_INDEX,
)

print(f"Playing tone at {FREQUENCY} Hz for {DURATION} seconds...")
time.sleep(1)


# Write the data to the stream (blocking mode)
stream.write(output_bytes)

print("Finished playing.")


# --- Cleanup ---
stream.stop_stream()
stream.close()
p.terminate()
