# RCP Task Acquisition

* [Overview](#overview)
* [Installation instructions](#installation)

## Overview
Code for the RCP task cart. More information to come...

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
    - `git clone https://github.com/mhelsel/rcp_task_acquisition.git`
    - `cd rcp_task_acquisition`
    - `pip install .`
3. Once installed, run with `python -m rcp_task_acquisition`

### First Run Setup
Note- in order to correctly run the program, all hardware must be installed
1. In **Select Protocol** panel select **Update Hardware**
2. Under **In Use** select each camera, assign their correct serial numbers, and select the primary/master camera
3. Select **Save Hardware Settings** and select **Close Hardware Panel**

