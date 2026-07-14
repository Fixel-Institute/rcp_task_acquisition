import datetime
import json
from pathlib import Path

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/ContinuousRecording") 

from psychopy import visual, gui, monitors
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import OpenIrisPythonClient, _parse_eccentricities, build_saccade_trials, build_fixation_block_trials, build_pursuit_trials, StimulusPresenter, ExperimentRunner
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import _dlg_saccade, _dlg_fixation, _dlg_pursuit, run_gaze_calibration

def get_saccade_config(v = ["8.0", 40, 1000, 0, 0, 1000, "random"]) -> dict:
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials": int(v[1]),
        "fix_dur_ms": int(v[2]),
        "fix_jitter_ms": int(v[3]),
        "gap_dur_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "balance": v[6],
    }

def get_pursuit_config(v = ["horizontal sinusoid", "alternating", 10.0, 12.0, 10.0, 8, 1000, 0, 3000]) -> dict:
    return {
        "pursuit_mode": v[0],
        "direction": v[1],
        "start_ecc": float(v[2]),
        "amplitude": float(v[3]),
        "speed": float(v[4]),
        "n_trials": int(v[5]),
        "fix_dur_ms": int(v[6]),
        "fix_jitter_ms": int(v[7]),
        "stim_dur_ms": int(v[8]),
    }

def get_fixation_config(v = ["10.0", "5.0", 20, 1000, 0, 1000, "random"]) -> dict:
    return {
        "horizontal_ecc": float(v[0]),
        "vertical_ecc": float(v[1]),
        "n_trials": int(v[2]),
        "fix_dur_ms": int(v[3]),
        "fix_jitter_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "order": v[6],
    }

def get_default_config(v = [100.0, 59.0, 2560, 1440, 0, "Saccade Block", "localhost", 9000, True, True, True, False, False, "oculostim", str(Path.home())]) -> dict:
    return {
        "screen_dist": float(v[0]),
        "screen_w_cm": float(v[1]),
        "screen_w_px": int(v[2]),
        "screen_h_px": int(v[3]),
        "screen_num": int(v[4]),
        "mode": v[5],
        "oi_host": v[6],
        "oi_port": int(v[7]),
        "oi_connect": bool(v[8]),
        "auto_record": bool(v[9]),
        "log_events": bool(v[10]),
        "do_calibrate": bool(v[11]),
        "sync_sq": bool(v[12]),
        "session": str(v[13]),
        "output_folder": str(v[14]),
    }

# Sets up display window, fixation cross, text pages and image stimuli
class OculoStim(bases.StimulusBase):
    def __init__(self, base_vars):
        super().__init__(**base_vars)
        self.trial = 0
        self.screen_width = 2200 #not technically screen width but we dont want to cover the photodiode
        self.screen_height = 1440

        self.trial_type = "Saccade"
        self.trial_data = []
        self.result_data = []

    def present_prep(self):
        cfg = get_default_config()

        """ Disabling OpenIRIS connection
        self.oi = OpenIrisPythonClient(cfg["oi_host"], cfg["oi_port"])
        if self.session_path != "":
            self.oi.change_dir(self.session_path)
        """
        mon = monitors.Monitor("oculostim", width=cfg["screen_w_cm"], distance=cfg["screen_dist"])
        mon.setSizePix((2560, 1440))
        self.display.monitor = mon
        
        if self.trial_type == "Saccade":
            cfg["mode"] = "Saccade Block"
            config = get_saccade_config()
            self.trial_data = build_saccade_trials(config)
        elif self.trial_type == "Fixation":
            cfg["mode"] = "Fixation Block"
            config = get_fixation_config()
            self.trial_data = build_fixation_block_trials(config)
        elif self.trial_type == "Pursuit":
            cfg["mode"] = "Pursuit Block"
            config = get_pursuit_config()
            self.trial_data = build_pursuit_trials(config)
        elif self.trial_type == "Calibration":
            cfg["mode"] = "Calibration"
            self.trial_data = []

        self.result_data = []
        self.presenter = StimulusPresenter(self.display)
        self.runner = ExperimentRunner(self.display, self.presenter, None, cfg)
        
    def present(self, test=True):
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()

        if self.trial_type == "Calibration":
            print("Running gaze calibration...")
            cal_model = run_gaze_calibration(self.display)
            if cal_model:
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    cal_path = f"D:\\RawDataLocal\\oculostim_calibration_{ts}.json"
                    print(f"Saving calibration data to {cal_path}...")
                    with open(cal_path, "w") as f:
                        json.dump(cal_model, f, indent=2)
                except Exception as e:
                    print(f"Failed to save calibration data: {e}")
                    logger.error(f"Failed to save calibration data: {e}")

        else:
            n = len(self.trial_data)
            i = 0
            while self.finish.value == 0 and i < n:
                #self.oi.start()
                trial = self.trial_data[i]
                self.runner.stim.set_status(
                    f"Trial {i + 1} / {n}   [{trial['type'].upper()}]")
                record = self.runner.run_trial(i, trial, draw_sync=self.display.draw_patch, flip_sync=self.display.switch_patch)
                #self.oi.stop()
                i += 1
                if record is None:
                    break
                self.result_data.append(record)

        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
    def saveMetadata(self, name, sessionFolder):
        return self.result_data
    
    def update_data(self, trial_data):
        self.trial_type = trial_data[1]