# RCP Task Acquisition

* [Overview](#overview)
* [Updates and Changes to Original Python Scripts](#Updates-and-Changes-to-Original-Python-Scripts)
* [Installation instructions](#installation)

## Overview
Code for the RCP task cart. More information to come...

## Updates and Changes to Original Python Scripts:

### Delsys Acquisition Script
- Delsys is now added. The Delsys sensor configurations require prior-connection, so the Delsys system must be connected in the Hardware Panel prior to running.
- Should we automate the whole process?... The issue is that sensors must be connected before we scan for sensors, otherwise the sensors are not registered by the base. The whole process is somewhat manual.

### Camera Packet Loss
- Camera Packet Loss is present in my computer even with only 1 Camera. 
- This is due to the fact that they try to add video writer in the same thread as the camera acquisition. 
- To fix this, we should use a thread-safe Producer-Consumer model where the camera acquisition is in one thread and the video writing is in another thread.

### Control Panel Buttons
- The control panels are all button-based, the best case scenario should be keyboard based so it is easier to start/stop/trigger

### Zombie Threads
- When the script crashed, the threading process is still processing despite the fact that Main thread has exited. 
- By default, Python threads are non-daemon threads. When your script "crashes" or reaches the end of its execution, the Python interpreter will not actually shut down as long as there is at least one non-daemon thread still running.
- To ensure that the program can exit cleanly, we can set the threads to be daemon threads. This way, when the main thread exits, all daemon threads will be automatically killed.

### General Feedbacks
- Currently, the LJ does not save configuration on the recording. This means that if the user changes the configuration, it will not be saved in the recording to notify user that a session is recorded with different sampling rate.
- The recording timestamp is date and session based, making timestamp difficult to track. We should at least save the timestamp somewhere. 
- The data are saved in text file which is significantly larger than binary files. We should save in binary format. 
- We need clarification on the Camera timestamps. 
- LJ is currently continuously recording even without task running.
- The Arduino Serial is honestly not necessary. I would like to remove this and just use the LJ for all digital I/O. This will simplify the system and reduce the number of potential points of failure.

## Installation
This is the outline for installing this program with the expected hardware configurations. There may be unexpected errors in the system if your hardware is different.

### Installing Windows
1. Install Windows 11 per University standards. It will be helpful to have some level of admin acess to install programs.
2. Adjust settings (Optional but recommended)
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
    - Choose **Videos** folder to extract to
4. Install other apps:
    - Notes:
        - When asked if you want app to make changes to the computer, always select **Yes**
        - Always accept any license during installation when prompted
        - Use all default settings unless stated here
    - NVIDIA Graphics Driver (580.88-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe)
    - Spinnaker SDK (SpinnakerSDK_FULL_4.0.189_x64.exe)
        - Deselect **Agree to allow analytics..** and select **next**
        - Select **Application Development** and select **next**
        - When finished the **Adapter Config Utility** menu may pop up. You can close this without modifying for right now, this is for GigE cameras
    - Anaconda (Anaconda3-2025.12-2-Windows-x86_64.exe)
    - Labjack (LabJack_2025-05-07.exe)
    - Git (Git-2.53.0.2-64-bit.exe)
    - VLC (vlc-3.0.23-win64.exe)
    - Visual Studio 2026
        - Download Installer at https://visualstudio.microsoft.com/downloads/
        - **Select Visual Studio Build Tools 2026** and select **Install**
5. Once all apps are installed, restart computer. You can now unplug the flash drive

### Installing Code
1. In the search bar at the bottom of the screen, search for and select **Anaconda Prompt**
2. The code can be installed in any part of computer but for following this installation, it will be installed in **Desktop**
    - `cd Desktop`
    - `conda create -n rcp_task_acquisition python=3.10`
    - `conda activate rcp_task_acquisition` - Note: This line will always need to be ran when running system in future
    - `git clone https://github.com/mmt-rcp/rcp_task_acquisition.git`
    - `cd rcp_task_acquisition`
    - `pip install .`
3. Once installed, run with `python -m rcp_task_acquisition`

### First Run Setup
Note- in order to correctly run the program, all hardware must be installed
1. In **Select Protocol** panel select **Update Hardware**
2. Under **In Use** select each camera, assign their correct serial numbers, and select the primary/master camera
3. Select **Save Hardware Settings** and select **Close Hardware Panel**

