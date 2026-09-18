# RCP Task Acquisition

* [Overview](#overview)
* [Installation instructions](#installation)
* [Labjack Defaults](#defaults)

## Overview
Code for the RCP task cart. More information to come...

## Installation
This is the outline for installing this program with the expected hardware configurations. There may be unexpected errors in the system if your hardware is different.

### Installing Windows
1. Install Windows 11 per University standards. It will be helpful to have some level of admin access to install programs.
    - If creating a local account instead of a university account DO NOT connect to wifi during installation. If you accidentally connect, you can press either Shift+Fn+F10 or press Shift+F10 and type `start ms-cxh:localonly`.
2. Adjust settings
    - Set Main Display:
        1. Go to **Settings -> System -> Display**
        2. Select the smaller screen
        3. Select the drop down for **Multiple displays**
        4. Check the box that says **Make this my main display**
    - Silence Notifications:
        1. Go to **Settings -> System -> Notifications**
        2. Turn Notifications **Off**
    - Turn Screen Sleep off
        1. Go to **Settings -> System -> Power**
        2. Expand the heading **Screen, sleep, & hibernate timeouts**
        3. Turn all settings here to **Never**

### Installing Programs
1. Plug in USB flash drive
2. When pop up with **Centon USB** shows up, select *Open device to view files. (If this pop up does not show up, you can also find in **File Explorer**). All apps other than Visual Studio will be installed from the versions on this USB.
3. Extract videos
    - Right-click **task_videos.zip**
    - Select **Extract All**
    - Choose **C:\Users\Public\Videos** (the Public Videos folder) to extract to.
4. Install other apps:
    - Notes:
        - When asked if you want app to make changes to the computer, always select **Yes**
        - Always accept any license during installation when prompted
        - Use all default settings unless stated here
    - NVIDIA Graphics Driver (580.88-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe)
    - Spinnaker SDK (4.4.0.246)
        - Download requires create account
        - Deselect **Agree to allow analytics..** and select **next**
        - Select **Application Development** and select **next**
        - When finished the **Adapter Config Utility** menu may pop up. You can close this without modifying for right now, this is for GigE cameras
    - Anaconda (Anaconda3-2025.12-2-Windows-x86_64.exe)
    - Labjack (LabJack_2025-05-07.exe)
    - Git (Git-2.53.0.2-64-bit.exe)
    - Git-LFS (https://github.com/git-lfs/git-lfs/releases)
      - current: https://github.com/git-lfs/git-lfs/releases/download/v3.8.0/git-lfs-windows-v3.8.0.exe
    - VLC (vlc-3.0.23-win64.exe)
5. Once all apps are installed, restart computer. You can now unplug the flash drive

### Installing Code
1. In the search bar at the bottom of the screen, search for and select **Anaconda Prompt**
2. The code can be installed in any part of computer but for following this installation, it will be installed in **Documents**
    - `cd Documents`  # Always
    - `conda create -n rcp-task-acquisition python=3.12`  # only first time
    - `conda activate rcp-task-acquisition` # Always
    - `conda install -c conda-forge pywinhook`  # only first time
      // other possibility is to get Visual C++ Build tools
    - `git lfs install`  # only first time, this enables git LFS hooks
    - `git clone https://github.com/mmt-rcp/rcp_task_acquisition.git`  # only first time
    - `cd rcp_task_acquisition`  # Always
    - `pip install -e . --find-links ./library`  # first time and when dependencies change
      # NB: using --find-linds to allow search for needed wheels within the current library subdir
      - **Only for DEV**:
        - Use `pip install -e .[dev] --find-links ./library` to get all dev tools included
        - `git config blame.ignoreRevsFile .git-blame-ignore-revs`  # only once/first time
        - `pre-commit install`  # only once/first time
   Temporary fix of psychopy -> vlc dependency:
    - `python ./library/patch_python_vlc.py`  # after python-vlc is installed
   Finally:
    - `create-shortcut`  # when shortcuts change
3. The final step in the terminal (`create-shortcut`) creates an icon on the Desktop which can be selected to run the code.
    - Alternatively, to run the program from command line, use `rcp-task-acquisition` (making sure you are in the conda environment)

### First Run Setup
Note: in order to correctly run the program, all hardware must be installed
1. In **Select Protocol** panel select **Update Hardware**
2. Under **In Use** select each camera, assign their correct serial numbers, and select the primary/master camera
3. Select **Save Hardware Settings** and select **Close Hardware Panel**
4. On first run, a folder will be created (RawLocalData) to store logs and session data. This folder will be in "C:\Users\Public\Documents".

## Defaults
The code should come with the defaults in labjack already specified, however if you change them and need to set them back this is the default configuration:
```
 Photodetector:
   labjack_input: AIN0
   voltage_range:
   - -0.015
   - 0.015
   graph: ''
 Subject Mic:
   labjack_input: AIN1
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 Experimenter Mic:
   labjack_input: AIN2
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 PC Audio:
   labjack_input: AIN3
   voltage_range:
   - -0.075
   - 0.075
   graph: ''
 Grip Force Sensor:
   labjack_input: AIN4
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 Force Sensor X:
   labjack_input: AIN5
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 Force Sensor Y:
   labjack_input: AIN6
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 Force Sensor Z:
   labjack_input: AIN7
   voltage_range:
   - -0.6
   - 0.6
   graph: ''
 Camera Sync TTL:
   labjack_input: FIO0
   voltage_range:
   - 0
   - 1
   graph: ''
 Grasp Start Pad:
   labjack_input: FIO1
   voltage_range:
   - 0
   - 1
   graph: ''
 Extra Digital In 1:
   labjack_input: FIO2
   voltage_range:
   - 0
   - 1
   graph: ''
 Extra Digital In 2:
   labjack_input: FIO3
   voltage_range:
   - 0
   - 1
   graph: ''
 Extra Digital Out:
   labjack_input: FIO4
   voltage_range:
   - 0
   - 1
   graph: ''
 Return From DS7A:
   labjack_input: FIO5
   voltage_range:
   - 0
   - 1
   graph: ''
 Trigger to DS7A:
   labjack_input: FIO6
   voltage_range:
   - 0
   - 1
   graph: ''
 TTL to E-Phys:
   labjack_input: FIO7
   voltage_range:
   - 0
   - 1
   graph: ''
 Digital Accessory:
   labjack_input: EIO0
   voltage_range:
   - 0
   - 1
   graph: ''
   ```

