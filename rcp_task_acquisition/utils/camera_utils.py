import pandas as pd
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

    expected_interval = 1e9 / frame_rate
    
    current_frame = len(timestamps_ns)
    timestamps_ns = np.asarray(timestamps_ns)
    
    dropped_frame_count = np.sum((np.round(timestamps_ns / expected_interval)) - 1)
    

    total_frames = current_frame+dropped_frame_count
    return dropped_frame_count, total_frames, current_frame


