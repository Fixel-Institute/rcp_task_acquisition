import ruamel.yaml
import shutil
import os

from rcp_task_acquisition.utils.constants import (STIM_CONFIG_FILE_PATH,
                             SCREEN_CONFIG_FILE_NAME,
                             CONFIG_FILE_PATH)
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./utils/file_utils") 


def get_screen_config():
    userDataDir = os.path.realpath(CONFIG_FILE_PATH)
    configPath = os.path.join(userDataDir, SCREEN_CONFIG_FILE_NAME)
    ruamelFile = ruamel.yaml.YAML()

    screen_config = None
    if os.path.exists(configPath):
        with open(configPath, 'r') as f:
            screen_config = ruamelFile.load(f)
    if screen_config is None:
        return
    return screen_config

def get_stimulus_config(filename):
    userDataDir = os.path.realpath(STIM_CONFIG_FILE_PATH)
    configPath = os.path.join(userDataDir, filename)
    ruamelFile = ruamel.yaml.YAML()

    stimulusConfig = None
    if os.path.exists(configPath):
        with open(configPath, 'r') as f:
            stimulusConfig = ruamelFile.load(f)
    if stimulusConfig is None:
        return
    return stimulusConfig

def copy_file(sessionFolder, filename):
    # Copy visual stimulus config file to session directory
    userDataDir = os.path.realpath(STIM_CONFIG_FILE_PATH)
    configPath = os.path.join(userDataDir, filename)
    shutil.copy2(
        configPath,
        os.path.join(sessionFolder, filename)
    )


def get_stimulus_path():
    return STIM_CONFIG_FILE_PATH

def get_config_path():
    return CONFIG_FILE_PATH

def write_config(config_name, data):
        config_path = os.path.join(CONFIG_FILE_PATH, config_name)
        with open(config_path, 'w') as config_file:
            ruamelFile = ruamel.yaml.YAML()
            ruamelFile.dump(data, config_file)
            
def read_config(config_name):
    config_path = os.path.join(CONFIG_FILE_PATH, config_name)
    ruamelFile = ruamel.yaml.YAML()
    if not(os.path.exists(config_path)):
        return None
    
    with open(config_path, 'r') as config_file:
        config = ruamelFile.load(config_file)
    return config

def write_metadata(folder, file_name, data):
    metadata_path = os.path.join(folder, file_name)
    with open(metadata_path, 'w') as metadata_file:
        ruamelFile = ruamel.yaml.YAML()
        ruamelFile.dump(data, metadata_file)


def cam_config_template():
    """
    Creates a template for config.yaml file. This specific order is preserved while saving as yaml file.
    """
    yaml_str = """\
# Camera reference (enter serial numbers for each)
    frontCam:
    sideCam:
    topCam:
    masterCam:
    \n
# Camera settings
    frontCrop:
    sideCrop:
    topCrop:
    exposure:
    framerate:
    bin:
    \n
# User information
    unitRef:
    raw_data_dir:
    COM:
    default_video_dir:
    \n
    
    """
    ruamelFile = ruamel.yaml.YAML()
    cfg_file = ruamelFile.load(yaml_str)
    return cfg_file, ruamelFile


def metadata_template():
    """
    Creates a template for config.yaml file. This specific order is preserved while saving as yaml file.
    """
    yaml_str = """\
# Version
    version:
    \n
    
# Cameras
    cameras:
    \n

# Experiment
    Designer:
    administrator_id:
    Task:
    StartTime:
    EndTime:
    Collection:
    duration (s):
    unitRef:
    \n

# Participant
    participant_id:
    participant_details:
    \n
    
# Screen Config
    screen_settings:
    \n

# Labjack Settings
    actual_scan_rate:
    hardware:
    \n

# Task
    task:
    task_settings:
    trial_data:
    task_notes:
    """
    
    ruamelFile = ruamel.yaml.YAML()
    cfg_file = ruamelFile.load(yaml_str)
    return cfg_file, ruamelFile

def read_metadata(path):
    ruamelFile = ruamel.yaml.YAML()
    if os.path.exists(path):
        with open(path, 'r') as f:
            cfg = ruamelFile.load(f)
    return(cfg)

