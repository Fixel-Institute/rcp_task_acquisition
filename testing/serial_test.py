import numpy as np
import pandas as pd

# Getting data from LabJack specific to our saving method
# filename = r'C:\Users\williar9\Downloads\labjack_data 1.txt'
filename = "/media/rld/c87215a7-5f3c-4acf-bb4d-2b823140e003/CompressedDataLocal/20260112/unitME/session055/20260112_unitME_session055_labjack.txt"

df = pd.read_csv(filename)  # auto-detects comma-delimited
bits = df["Digital"].astype(np.uint8).to_numpy()
digital_reshape = np.unpackbits(bits.view(np.uint8)).reshape(8, np.shape(bits)[0], order="F")[::-1]


# Bits must be the digital read from the Arduino as a single vector
bits = digital_reshape[7, :]


fs = 40_064  # DAQ sampling frequency
baud = 2400  # Arduino TX out baudrate

min_idle_bits = 1
window_radius = 2
bits = np.asarray(bits).astype(int)
N = len(bits)
samples_per_bit = fs / float(baud)
idle = 1  # idle level after inversion

byte_list = []
curr_idx = 0

while curr_idx < N - 1:
    curr_idx += 1
    # Look for idle -> 0 edge: possible start bit
    if bits[curr_idx - 1] == idle and bits[curr_idx] == 0:
        # Optional: check some idle before start to avoid false triggers
        idle_samples_needed = int(min_idle_bits * samples_per_bit)
        if idle_samples_needed > 0:
            idle_start = max(0, curr_idx - idle_samples_needed)
            if not np.all(bits[idle_start:curr_idx] == idle):
                continue

        bit_vals = []
        ok = True
        for n in range(10):  # start, 8 data, stop
            center_f = curr_idx + (n + 0.5) * samples_per_bit
            center = round(center_f)

            # Majority vote in a small window around center
            lo = max(0, center - window_radius)
            hi = min(N, center + window_radius + 1)
            if lo >= hi:
                ok = False
                break
            window = bits[lo:hi]
            bit_val = int(np.mean(window) >= 0.5)
            bit_vals.append(bit_val)

        if ok:
            start_bit = bit_vals[0]
            stop_bit = bit_vals[9]

            if start_bit == 0 and stop_bit == idle:
                # Data bits LSB-first
                byte_val = 0
                for k, b in enumerate(bit_vals[1:9]):
                    if b:
                        byte_val |= 1 << k
                byte_list.append((byte_val, curr_idx))

        # Skip slightly less than one full frame
        # to ensure we catch the start of the next one
        curr_idx += round(9.5 * samples_per_bit)
        continue

# ---------------------------------------
# Quick sanity check: view decoded text
# ---------------------------------------
max_chars = 300
bytes_list = [b for (b, _) in byte_list]
text = "".join(chr(b) for b in bytes_list)
print("First decoded characters:")
print(repr(text[:max_chars]))

protocol = None
timestamps = []

line_chars = []
line_start = None

for byte_val, start_idx in byte_list:
    ch = chr(byte_val)

    if line_start is None:
        line_start = start_idx

    if ch == "\n":
        line = "".join(line_chars)

        # First P-line before timestamps
        if line.startswith("P"):
            print(line_start / 40000)
            protocol = line
        # Timestamp: Tssss
        elif line.startswith("T") and len(line) >= 5:
            seconds = int(line[1:5])
            timestamps.append({"seconds": seconds, "start_sample": line_start})

        line_chars = []
        line_start = None
    else:
        line_chars.append(ch)
timestamps_df = pd.DataFrame(timestamps)
if protocol == None:
    print("Protocol not found")
else:
    protocol = protocol[1:-1]
    print(protocol)
print(timestamps_df)  # -*- coding: utf-8 -*-
