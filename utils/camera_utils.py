import pandas as pd
from models.Warnings import Warning
import numpy as np

def identify_dropped_frames(timestamp_file, frame_rate):
    """
    Identify dropped frames in a video based on inter-frame intervals.
 
    Parameters:
        timestamp_file (str): Path to the CSV file containing timestamps in nanoseconds.
        frame_rate (float): Expected frame rate in frames per second.
 
    Returns:
        frame_count (int): Number of dropped frames. 
    """
    # Load timestamps from the file
    timestamps_ns = pd.read_csv(timestamp_file, header=None, names=['timestamp'])['timestamp'].values  # Extract timestamp column
    # frame_count = 0
    # Calculate the expected inter-frame interval
    expected_interval = 1e9 / frame_rate
    
    current_frame = len(timestamps_ns)
    timestamps_ns = np.asarray(timestamps_ns)
    
    dropped_frame_count = np.sum((np.round(timestamps_ns / expected_interval)) - 1)
    
    # # Mark dropped frames
    # current_frame = 0
    # total_frames = 0
    # for i, interval in enumerate(timestamps_ns):
    #     current_frame += 1
    #     if interval > 1.5 * expected_interval:  # Dropped frame threshold
    #         # Calculate how many frames were missed
    #         frame_count += int(round(interval / expected_interval)) - 1
    total_frames = current_frame+dropped_frame_count
    return dropped_frame_count, total_frames, current_frame


