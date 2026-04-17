# -*- coding: utf-8 -*-
import os
from psychopy import core
from pathlib import Path



BASEDIR = Path(__file__).resolve().parent.parent.parent.parent.parent
CODE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = os.path.join( "D:", "RawDataLocal")

STIM_CONFIG_FILE_PATH = CONFIG_FILE_PATH = os.path.join(CODE_DIR.resolve().parent, 'config_files')
STIM_CONFIG_FILE_NAME = 'visualStimulusConfig.yaml'
SCREEN_CONFIG_FILE_NAME = "screen_config.yaml"
VIDEO_DIR = os.path.join(BASEDIR, "Videos", "task_videos")

# constants for graphing
DEFAULTS = ["Microphone 1", "Audio", "TENS"]
PLOT_CONSTANTS = ["Cameras", "Barcode", "Photodiode"]
LINE_STYLES = ["-", "-", "-", "-"] #["--", "-", ":", "-."]
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#8c564b',  '#9467bd', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#9467bd', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#7f7f7f', '#bcbd22', '#17becf']
PLOT_LENGTH = 80000

# labjack constants
SCANS_PER_READ = 10000
#Hardcoded the hardware and labjack bc its much easier than pulling from somewhere for now
CAMERA_HEADERS = ["In Use","Name", "Is Primary", "Serial Number"]
HEADERS = ["In Use", "Hardware", "Labjack Pin", "Voltage Range"]#"Graph Min", "Graph Max"]
HARDWARE_LIST = ["Audio", "Cameras", "Button", "Photodiode", 
                 "Grasp Button", "Microphone 1", "Microphone 2", 
                 "String Potentiometer", "Force Sensor X", "Force Sensor Y", 
                 "Force Sensor Z", "Barcode", "TENS", "TENS-out"]
LABJACK_PIN_LIST = ["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", 
                    "FIO0", "FIO1", "FIO2", "FIO3", "FIO4", "FIO5", "FIO6", "FIO7",
                    "EIO0", "EIO1", "EIO2", "EIO3", "EIO4", "EIO5", "EIO6", "EIO7"]

    
ANALOG_RANGES = [11, 9.6, 4.8, 2.4, 1.2, 0.6, 0.3, 0.15, 0.075, 0.036, 0.015]



#constants for gui layout
RGB_COLOR = (54, 54, 54)


# shorter name for the global clock
GLOBAL_CLOCK = core.monotonicClock


# sound constants
VOLUME = 0.125       # range [0.0, 1.0]
SAMPLING_RATE = 44100 # sampling rate, Hz
DURATION = 1# in seconds, can be a float
FREQUENCY = 750   # sine frequency, Hz, can be a float



# serial constants
BAUDRATE = 9600
WRITE_TIMEOUT = 0.1




