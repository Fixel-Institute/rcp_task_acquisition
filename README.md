# RCP Task Acquisition

* [Overview](#overview)
* [Installation](#installation)
* [Running the program](#running-the-program)
* [Optional settings (.env)](#optional-settings-env)
* [Where data is saved](#where-data-is-saved)
* [OculoStim (eye tracking task)](#oculostim-eye-tracking-task)
* [Troubleshooting](#troubleshooting)
* [Labjack Defaults](#defaults)

## Overview
Code for the RCP task cart. A wxPython control window runs the tasks while a
separate PsychoPy process draws the stimuli on the participant screen. During
each task it records the cameras (Spinnaker), LabJack signals (photodiode,
microphones, force sensors, TTLs), and, if present, Delsys sensors and the
OpenIris eye tracker.

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
    - .NET 8 Desktop Runtime, Windows x64 (from Microsoft, dotnet.microsoft.com). Needed
      by the Delsys code, which starts .NET 8 when the program opens. Check with
      `dotnet --list-runtimes` (look for `Microsoft.NETCore.App 8.`).
    - Eye tracking carts only: OpenIris, one of Fixel's builds in this repo. Unzip it somewhere
      permanent and run `Release\OpenIris.exe`. Both builds have the Spinnaker (FLIR) camera
      plugin (`Plugins/SpinnakerInterface.dll`, eye tracker system "Spinnaker Dual Camera") and
      the remote commands OculoStim uses (SETDATAFOLDER, STARTTRACKING, STOPTRACKING, GETDATA)
      on UDP port 9003 (OpenIris's ServiceListeningPort + 3).
      - `library/OpenIris_Win_Release_0.1.5_SpinnakerMod.zip`: tested with OculoStim on the
        UCSF cart.
      - `library/OpenIris_Win_Release_0.2.0_SpinnakerMod.zip`: has the Spinnaker plugin since
        the 11/20/2026 update (the earlier 0.2.0 zip did not, so no cameras appeared). Not yet
        tested with OculoStim.
      - Stock OpenIris answers `Unknown command 'STARTTRACKING'` (in its log); recording
        still works but tracking and the data folder can't be set remotely.
      - Camera orientation is set in OpenIris (LeftEyeOrientation / RightEyeOrientation in the
        eye tracking system settings); OpenIris overrides flips set in SpinView.
5. Once all apps are installed, restart computer. You can now unplug the flash drive

### Installing Code
1. In the search bar at the bottom of the screen, search for and select **Anaconda Prompt**.
   All commands below are run there (not in a plain Command Prompt or PowerShell).
2. The code can be installed in any part of computer but for following this installation, it will be installed in **Documents**
    - `cd Documents`  # Always
    - `conda create -n ucsf-rcp-task-acquisition python=3.12`  # only first time
    - `conda activate ucsf-rcp-task-acquisition` # Always
    - `conda install -c conda-forge pywinhook`  # only first time
      // other possibility is to get Visual C++ Build tools
    - `git lfs install`  # only first time, this enables git LFS hooks
    - `git clone https://github.com/zigsK/rcp_task_acquisition.git`
    - `cd rcp_task_acquisition`  # Always
    - `pip install -e . --find-links ./library`  # first time, and after every `git pull` that changes pyproject.toml
      # NB: --find-links lets pip use the wheels in the library subdir (Spinnaker)
      # This also installs pythonnet and python-dotenv, and makes the top-level
      # `library` folder (Delsys, BRAVO) importable, so the program can be started
      # from any folder.
      - **Only for DEV**:
        - Use `pip install -e .[dev] --find-links ./library` to get all dev tools included
        - `git config blame.ignoreRevsFile .git-blame-ignore-revs`  # only once/first time
        - `pre-commit install`  # only once/first time
   Temporary fix of psychopy -> vlc dependency:
    - `python ./library/patch_python_vlc.py`  # after python-vlc is installed
   Fix of pyglet text on Python 3.12 (otherwise any on-screen text crashes a task):
    - `python ./library/patch_pyglet_py312.py`  # after every `pip install -e .`
   Finally:
    - `create-shortcut`  # when shortcuts change

To update an existing install: `cd` into the folder, `conda activate ucsf-rcp-task-acquisition`,
`git pull`, `pip install -e . --find-links ./library`, then `python ./library/patch_pyglet_py312.py`.

### First Run Setup
Note: in order to correctly run the program, all hardware must be installed
1. In **Select Protocol** panel select **Update Hardware**
2. Under **In Use** select each camera, assign their correct serial numbers, and select the primary/master camera
3. Select **Save Hardware Settings** and select **Close Hardware Panel**
4. Check `RawDataDir` (where session data goes) and `VideoDir` in `config_files/userdata.yaml`. The default `RawDataDir` is `D:\RawDataLocal`.

## Running the program
There is no .exe. Either:
- double-click the Desktop icon made by `create-shortcut` (**UCSF-UF RCP Task Acquisition**), or
- in the Anaconda Prompt: `conda activate ucsf-rcp-task-acquisition`, then `rcp-task-acquisition`.

Running from the Anaconda Prompt shows all messages, which helps when something goes wrong.

On a cart without a Delsys license these lines at startup are expected, and the program keeps going:
```
DelsysAPI: Failed to validate key/license
ERROR | ./models/DelsysProcess | Error connecting to Delsys device
ERROR | ./panels/SwitchPanel | Delsys NOT CONNECTED
```

## Optional settings (.env)
Keys that should not be in git go in a file named `.env` in the repo folder (it is in `.gitignore`).
It is read when the program starts. Leave out what you don't use.
```
DelsysKey=...
DelsysLicense=...
BRAVOAccessKey=...
BRAVOServer=...
OpenIrisHost=127.0.0.1
OpenIrisPort=9003
```
- `DelsysKey` / `DelsysLicense`: Delsys Trigno sensors. Without them Delsys is skipped (see above).
- `BRAVOAccessKey` / `BRAVOServer`: only for uploading sessions to BRAVO (Upload Data).
- `OpenIrisHost` / `OpenIrisPort`: where OculoStim sends OpenIris commands. The default
  `127.0.0.1:9003` is right when OpenIris runs on the same PC with its default port
  (OpenIris listens on its ServiceListeningPort + 3).

## Where data is saved
Each task run gets its own session folder:
```
<RawDataDir>\<YYYYMMDD>\<unitRef>\sessionNNN (<task name>)
```
`RawDataDir` and `unitRef` are set in `config_files/userdata.yaml`.

## OculoStim (eye tracking task)
Select the OculoStim task, then start a block with one of the buttons on its panel:
**Calibrate (online)**, **Calibrate (offline)**, **Saccades**, **Smooth Pursuit** or
**Fixation**. While a block runs, the
panel shows which one, the other buttons are disabled, and a **Stop Block** button ends it
early.

OculoStim always records the face cameras only (`leftCamFace`, `rightCamFace`, plus the
master camera if it is a different one), whatever `config_files/taskconfig.yaml` lists.

Start OpenIris (Fixel SpinnakerMod build, see above) before **Start Task**. OculoStim
controls it over UDP on `127.0.0.1:9003`:
- **Start Task**: sets the session folder and starts tracking, so you can check the eye
  images in OpenIris and adjust the setup before running any block.
- **Each block**: checks camera frames are coming in, starts recording, and stops
  recording when the block ends (one `SESSION_NAME-...` folder per block).
- **Stop Task**: stops tracking.

In the Anaconda Prompt you should see:
```
Session path set to: ...
OPENIRIS: STARTTRACKING sent at task start (try 1).
OPENIRIS: tracking - check the eye images in OpenIris.
(each block)
OPENIRIS: tracking (127.0.0.1:9003).
OPENIRIS: STARTRECORDING sent; recording folder: ...
OPENIRIS: STOPRECORDING sent (tracking continues until Stop Task).
```
If OpenIris isn't reachable, or no frames come in, an `OPENIRIS:` line says which. The
block still runs, but check OpenIris before the next one. The result is also saved with
the block (`openiris` in the metadata).

**Calibrate (offline)** runs the original timed 9-dot sequence (no live gaze, nothing to
check during the session); the dot positions and times are saved in
`oculostim_calibration_<timestamp>.json` and OpenIris records the block as usual.

**Calibrate (online)** runs on its own, without a keypress:
1. 9 calibration dots. A per-eye fit maps pupil position to degrees.
2. 5 check dots: (0,0), (±10,0) and (0,±5) degrees.
3. A result screen for 8 s with the error for each eye. It passes if the mean error is
   ≤ 2° and the worst dot is ≤ 3°; otherwise it says to press Calibrate (online) to redo.

If OpenIris sends no live gaze within 5 s, it falls back to the older dot sequence that
is calibrated afterwards (offline).

Files written to the session folder:

| File | What it is |
|---|---|
| `SESSION_NAME-<date>-<time>\` | OpenIris recording for that block (one per block) |
| `oculostim_onlinecal_<timestamp>.json` | Online calibration: fit, check-dot errors, pass/fail |
| `oculostim_calibration_<timestamp>.json` | Calibration dot positions and times (same format as before) |
| `oculostim_targets_<block>_<timestamp>.csv` | Every change of what was on screen: target position (degrees and pixels) with its frame time |

If the program has no session folder, OculoStim saves to
`D:\RawDataLocal\oculostim_no_session\<YYYYMMDD>` (or the home folder if there is no D: drive).

Block settings (eccentricities, number of trials, fixation durations, pursuit amplitude and
speed) are the defaults in `src/rcp_task_acquisition/tasks/OculoStim/OculoStim.py`.
A photodiode square flips at each fixation onset and target onset (two flips per pursuit trial).

## Troubleshooting
| Message | Cause and fix |
|---|---|
| `rcp-task-acquisition` is not recognized | The conda environment isn't active, or `pip install -e . --find-links ./library` wasn't run in it. |
| `No module named 'library'`, `pythonnet`, `BRAVOClient` or `dotenv` | Installed from an older version. Run `git pull`, then `pip install -e . --find-links ./library`. |
| `Fatal error. Internal CLR error. (0x80131506)` | Two .NET versions loaded in one program. Check that .NET 8 is installed and that the code is up to date (OculoStim no longer loads the old OpenIris .NET DLL). |
| `No module named 'Aero'` | The Delsys DLL was loaded after another .NET runtime had started; same cause as above. |
| `expected LP_c_ubyte instance instead of c_byte_Array_...` (from `pyglet\font\win32.py`) | pyglet 1.4.11 on Python 3.12. Run `python ./library/patch_pyglet_py312.py`. |
| OculoStim: `no reply from OpenIris` / `OpenIris did not answer` | OpenIris isn't running, or its remote port isn't 9003 (set `OpenIrisPort` in `.env`). |
| OculoStim: `answered but did not start tracking` | OpenIris got STARTTRACKING twice and refused it. Its log has a line `ERROR: remote command 'STARTTRACKING' failed: ...` with the reason. Pressing Start in OpenIris works too; blocks still record. |
| OculoStim: `answered but no frames came in` | OpenIris got the commands but the cameras aren't streaming. Check them in OpenIris; a stock (non-Fixel) build ignores STARTTRACKING. |

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

