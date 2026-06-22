from pathlib import Path

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/ContinuousRecording") 

from psychopy import visual, gui
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import _parse_eccentricities, build_saccade_trials, build_fixation_block_trials, build_pursuit_trials, StimulusPresenter, ExperimentRunner
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import _dlg_saccade, _dlg_fixation, _dlg_pursuit
def get_saccade_config(v = ["10.0", 20, 1000, 0, 0, 1000, "interleaved"]) -> dict:
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials":       int(v[1]),
        "fix_dur_ms":     int(v[2]),
        "fix_jitter_ms":  int(v[3]),
        "gap_dur_ms":     int(v[4]),
        "stim_dur_ms":    int(v[5]),
        "balance":        v[6],
    }

def get_default_config(screen_dist=57.0, screen_w_cm=52.7, screen_w_px=1920, screen_h_px=1080):
    return {
        "screen_dist":   float(screen_dist),
        "screen_w_cm":   float(screen_w_cm),
        "screen_w_px":   int(screen_w_px),
        "screen_h_px":   int(screen_h_px),
        "screen_num":    int(0),
        "mode":          "Saccade Block",
        "oi_host":       "127.0.0.1",
        "oi_port":       int(9003),
        "oi_connect":    bool(False),
        "auto_record":   bool(True),
        "log_events":    bool(True),
        "do_calibrate":  bool(False),
        "sync_sq":       bool(False),
        "session":       str("oculostim"),
    }


# Sets up display window, fixation cross, text pages and image stimuli
class OculoStim(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame, None, finish)
        self.trial = 0
        self.screen_width = 2200 #not technically screen width but we dont want to cover the photodiode
        self.screen_height = 1440

        self.trial_type = "Saccade"
        self.trial_data = []
        self.result_data = []
    
    def present_prep(self):
        cfg = get_default_config()
        if self.trial_type == "Saccade":
            cfg["mode"] = "Saccade Block"
            config = _dlg_saccade()
            self.trial_data = build_saccade_trials(config)
        elif self.trial_type == "Fixation":
            cfg["mode"] = "Fixation Block"
            config = _dlg_fixation()
            self.trial_data = build_fixation_block_trials(config)
        elif self.trial_type == "Pursuit":
            cfg["mode"] = "Pursuit Block"
            config = _dlg_pursuit()
            self.trial_data = build_pursuit_trials(config)
        
        self.result_data = []
        self.presenter = StimulusPresenter(self.display)
        self.runner = ExperimentRunner(self.display, self.presenter, None, cfg)
        
    def present(self, test=True):
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        
        n = len(self.trial_data)
        i = 0
        while self.finish.value == 0:
            trial = self.trial_data[i]
            self.runner.stim.set_status(
                f"Trial {i + 1} / {n}   [{trial['type'].upper()}]")
            record = self.runner.run_trial(i, trial, draw_sync=self.display.draw_patch, flip_sync=self.display.switch_patch)
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