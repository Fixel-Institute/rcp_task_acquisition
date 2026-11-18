# ============================================================
# CHANGE LOG
#   11.11.26: online calibration + validation (replaces the
#             offline-only "Calibration" trial type, which is
#             kept as a fallback) and target-position logging for
#             the Saccade / Fixation / Pursuit blocks. See the
#             block below the imports.
#   11.17.26: pursuit amplitude default 12 -> 10 deg (the source
#             now uses this value; 10 deg is what was always
#             shown). Fixation duration defaults 1000 + 0 jitter
#             -> 800 + 0-400 ms jitter (the source now uses these;
#             800-1200 ms is what was always shown).
#   11.18.26: calibration no longer waits for a key press (keys
#             don't reach the PsychoPy window once the operator
#             uses the GUI buttons in panel.py). One attempt per
#             Calibration block: the result shows for
#             CAL_RESULT_SHOW_S seconds, then the block ends. To
#             redo, start another Calibration block. Each attempt
#             is saved and marked passed / not passed.
#   11.18.26: checked against OpenIris 0.2.0 (Fixel's
#             SpinnakerMod build has every command used here,
#             incl. SETDATAFOLDER / STARTTRACKING, and GETDATA
#             replies in the format parsed below). Calibration now
#             waits up to GAZE_WAIT_S for tracking to start before
#             falling back to offline, and keeps each sample's
#             OpenIris frame number and time.
#   11.18.26: session folder. The session path now arrives after
#             OculoStim is created (StimulusThread fix, same date)
#             and is applied by set_session_path: OpenIris is told
#             to record there (one SESSION_NAME-<date>-<time>
#             folder per block, where deidentify_dates.py expects
#             them) and OculoStim's own files are saved there. It
#             is re-sent before every block. If the path is still
#             empty, OculoStim's files go to a fallback folder
#             (oculostim_no_session) instead of failing to save, as
#             the calibration file did in an earlier session.
#   Every changed line is marked with its date below (11.11.26
#   also removed trailing spaces on blank lines, no effect). The
#   original file is OculoStim_before_online_cal.py.
# ============================================================

from datetime import datetime
import csv                  # 11.11.26: added (target log)
import json
import math                 # 11.11.26: added
import random               # 11.11.26: added (validation order)
import socket               # 11.11.26: added (live gaze over UDP)
import time                 # 11.11.26: added (unix timestamps)
from pathlib import Path

import numpy as np          # 11.11.26: added (calibration fit)

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/ContinuousRecording") 

from psychopy import visual, gui, monitors, core, event     # 11.11.26: added core, event
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import OpenIrisPythonClient, _parse_eccentricities, build_saccade_trials, build_fixation_block_trials, build_pursuit_trials, StimulusPresenter, ExperimentRunner
from rcp_task_acquisition.tasks.OculoStim.oculostim_source import _dlg_saccade, _dlg_fixation, _dlg_pursuit, run_gaze_calibration


# ============================================================
# 11.11.26: ADDED - ONLINE CALIBRATION + TARGET LOGGING
#
# Calibration (trial type "Calibration"):
#   1. 9-point grid, same dot positions as the old routine
#      (15/50/85% of the screen), so offline analysis still
#      works. Live gaze is read from OpenIris on every frame.
#   2. Affine fit, pupil px -> deg, per eye. Error =
#      leave-one-dot-out (as in gazeCalibration.py).
#   3. Validation: 5 new dots at the task positions (centre,
#      +/-10 deg horizontal, +/-5 deg vertical). Error = distance
#      between calibrated gaze and the dot.
#   4. Results screen. (11.18.26: was SPACE/ENTER = accept,
#      R = redo, ESC = stop.) Now shown for CAL_RESULT_SHOW_S
#      seconds, then the block ends; redo = run another
#      Calibration block. Every attempt is saved, passed or not.
#   If no live gaze is available, falls back to the old
#   (offline) routine so the session still gets a calibration.
#
#   Files in the session folder:
#     oculostim_calibration_<time>.json   dot list, same format
#        as before; written right after the 9 dots so
#        gazeCalibration.py still finds the run
#     oculostim_onlinecal_<time>.json     everything: dot
#        onset times, raw samples, fits, errors, validation
#   A summary also goes into result_data (metadata.yaml).
#
# Target logging (Saccade / Fixation / Pursuit):
#   Every frame where what's on screen changes (fixation cross,
#   target dot, blank), the time right after the flip and each
#   item's position are written to
#     oculostim_targets_<trial type>_<time>.csv
#   Positions: as drawn (psychopy units), screen px from the
#   centre (+ = right/up), and true visual angle,
#   atan(cm / distance). PsychoPy "deg" units use a linear
#   approximation, so true angles are smaller than the drawn
#   values at large eccentricities.
#   Each trial record also gets the target's onset time and
#   position (first frame the dot appears).
#
# Photodiode patch: flipped at each calibration dot's onset and
# offset (an even number of flips, so it ends as it started).
# ============================================================

CAL_FRACS = [
    (0.15, 0.15), (0.50, 0.15), (0.85, 0.15),
    (0.15, 0.50), (0.50, 0.50), (0.85, 0.50),
    (0.15, 0.85), (0.50, 0.85), (0.85, 0.85),
]
VAL_POINTS = [(0.0, 0.0), (10.0, 0.0), (-10.0, 0.0), (0.0, 5.0), (0.0, -5.0)]   # deg, task positions

CAL_SETTLE_S = 1.0          # time to get to the dot (samples ignored)
CAL_COLLECT_S = 1.0         # samples used for the dot
MIN_VALID_FRAC = 0.5        # share of frames with a tracked pupil
MIN_DOTS_FOR_FIT = 6

PASS_MEAN_DEG = 2.0         # validation: mean error
PASS_MAX_DEG = 3.0          # validation: worst dot
CAL_RESULT_SHOW_S = 8.0     # 11.18.26: added - how long the result stays on screen

GAZE_WAIT_S = 5.0           # 11.18.26: added - wait for tracking to start (was 1 s)
OPENIRIS_UDP = ("127.0.0.1", 9003)    # same address OpenIrisPythonClient sends commands to


def _f(v):
    """float, or nan for missing / untracked (OpenIris writes 0)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return math.nan
    return v if math.isfinite(v) and v > 0 else math.nan


def _xy(obj):
    if not isinstance(obj, dict):
        return math.nan, math.nan
    c = obj.get("Center") or obj.get("center") or obj
    return _f(c.get("X", c.get("x"))), _f(c.get("Y", c.get("y")))


def _parse_eye(d, eye):
    """
    Pupil and first corneal reflection (px) for one eye from an
    OpenIris data packet. Handles flat packets (LeftPupilX, as
    in the recording files) and nested ones (Left: {Pupil: ...}).
    """
    if f"{eye}PupilX" in d:
        return (_f(d.get(f"{eye}PupilX")), _f(d.get(f"{eye}PupilY")),
                _f(d.get(f"{eye}CR1X")), _f(d.get(f"{eye}CR1Y")))

    e = (d.get(eye) or d.get(eye.lower()) or d.get(f"{eye}Eye") or d.get(f"{eye.lower()}Eye") or {})
    if not isinstance(e, dict):
        return (math.nan,) * 4

    if "Pupil" in e or "pupil" in e:
        px, py = _xy(e.get("Pupil") or e.get("pupil"))
    else:
        px, py = _f(e.get("X", e.get("x"))), _f(e.get("Y", e.get("y")))

    cr = e.get("CRs") or e.get("CornealReflections") or e.get("CR") or e.get("cr")
    if isinstance(cr, list):
        cr = cr[0] if cr else None
    cx, cy = _xy(cr) if cr else (math.nan, math.nan)

    return px, py, cx, cy


class LiveGaze:
    """
    Latest gaze sample from OpenIris. (11.17.26) OpenIrisPythonClient only
    sends commands (no replies), so this asks the OpenIris UDP
    remote directly (GETDATA, port 9003, as the older OculoStim
    did). A live-data method on the client is used instead if
    one is ever added.
    11.18.26: OpenIris 0.2 replies to GETDATA with
      {"Left": {"FrameNumber", "Seconds", "Pupil": {"Center":
      {"X", "Y"}, ...}, "CRs": [{"X", "Y"}, ...]}, "Right": ...}
    with zeros when an eye isn't tracked (read as missing here).
    (Removed: the note that the .NET OpenIrisClient was the next
    option. OpenIris 0.2 removed that service, port 9000.)
    """
    METHODS = ("get_data", "get_eye_data", "get_current_data", "get_latest_data", "get_gaze")

    def __init__(self, client):
        self.fn, self.source, self._sock = None, None, None

        for m in self.METHODS:
            f = getattr(client, m, None)
            if callable(f):
                self.fn, self.source = f, f"OpenIrisPythonClient.{m}"
                break

        if self.fn is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(0.05)
            self.source = f"UDP GETDATA {OPENIRIS_UDP[0]}:{OPENIRIS_UDP[1]}"

    def _raw(self):
        if self.fn is not None:
            return self.fn()
        self._sock.sendto(b"GETDATA", OPENIRIS_UDP)
        data, _ = self._sock.recvfrom(65536)
        return data

    def read(self):
        """Dict of lpx, lpy, lcx, lcy, rpx, rpy, rcx, rcy (nan if not tracked), or None."""
        try:
            d = self._raw()
            if isinstance(d, (bytes, bytearray)):
                d = d.decode("ascii", errors="ignore")
            if isinstance(d, str):
                d = json.loads(d)
            if not isinstance(d, dict):
                return None
        except Exception:
            return None

        lpx, lpy, lcx, lcy = _parse_eye(d, "Left")
        rpx, rpy, rcx, rcy = _parse_eye(d, "Right")

        out = dict(lpx=lpx, lpy=lpy, lcx=lcx, lcy=lcy, rpx=rpx, rpy=rpy, rcx=rcx, rcy=rcy)

        # 11.18.26: added - OpenIris frame number and camera time
        # of the sample, to line samples up with the recording file
        for eye, p in (("Left", "l"), ("Right", "r")):
            e = d.get(eye) if isinstance(d.get(eye), dict) else {}
            fr, sec = e.get("FrameNumber"), e.get("Seconds")
            out[f"{p}_frame"] = int(fr) if isinstance(fr, (int, float)) else None
            out[f"{p}_seconds"] = float(sec) if isinstance(sec, (int, float)) else None
        return out

    def close(self):
        if self._sock:
            self._sock.close()


def _affine(px, dots):
    """Least-squares affine map, eye px -> deg. Returns 3x2 coefficients."""
    A = np.c_[px, np.ones(len(px))]
    return np.linalg.lstsq(A, dots, rcond=None)[0]


def _apply(coef, px):
    return np.c_[px, np.ones(len(px))] @ coef


def _leave_one_out(px, dots):
    err = []
    for k in range(len(px)):
        m = np.arange(len(px)) != k
        err.append(_apply(_affine(px[m], dots[m]), px[k:k + 1])[0] - dots[k])
    return np.array(err)


def _r(v, n=4):
    """Rounded float for json/yaml (None for nan)."""
    v = float(v)
    return round(v, n) if math.isfinite(v) else None


class ScreenGeometry:
    """Converts a position as drawn (psychopy units) to screen px and true visual angle."""

    def __init__(self, win):
        self.win = win
        mon = win.monitor
        self.w_cm = float(mon.getWidth())
        self.dist_cm = float(mon.getDistance())
        self.px_w, self.px_h = (int(v) for v in mon.getSizePix())
        self.cm_per_px = self.w_cm / self.px_w

    def to_px(self, x, y, units):
        try:
            from psychopy.tools.monitorunittools import convertToPix
            p = convertToPix(vertices=np.zeros(2), pos=np.array([x, y], dtype=float), units=units, win=self.win)
            return float(p[0]), float(p[1])
        except Exception:
            from psychopy.tools.monitorunittools import deg2pix
            return float(deg2pix(x, self.win.monitor)), float(deg2pix(y, self.win.monitor))

    def px_to_true_deg(self, px):
        return math.degrees(math.atan(px * self.cm_per_px / self.dist_cm))

    def describe(self, x, y, units):
        xp, yp = self.to_px(x, y, units)
        return dict(x_drawn=_r(x), y_drawn=_r(y), units=units, x_px=_r(xp, 2), y_px=_r(yp, 2),
                    x_deg_true=_r(self.px_to_true_deg(xp)), y_deg_true=_r(self.px_to_true_deg(yp)))


class LoggingPresenter(StimulusPresenter):
    """
    StimulusPresenter that remembers what was drawn on each frame.
    TargetLog (below) writes it out after the flip.
    """

    def __init__(self, win, *args, **kwargs):
        super().__init__(win, *args, **kwargs)
        self.frame_items = []

    def _units(self, name):
        return getattr(getattr(self, name, None), "units", None) or "deg"

    def draw_fixation(self, *args, **kwargs):
        out = super().draw_fixation(*args, **kwargs)
        x = args[0] if len(args) > 0 else kwargs.get("x", 0.0)
        y = args[1] if len(args) > 1 else kwargs.get("y", 0.0)
        self.frame_items.append(("fixation", float(x), float(y), self._units("_fix_h")))
        return out

    def draw_dot(self, *args, **kwargs):
        out = super().draw_dot(*args, **kwargs)
        x = args[0] if len(args) > 0 else kwargs.get("x")
        y = args[1] if len(args) > 1 else kwargs.get("y")
        if x is not None and y is not None:
            self.frame_items.append(("dot", float(x), float(y), self._units("_dot")))
        return out


class TargetLog:
    """
    Wraps the window's flip. After each flip, if what was drawn
    differs from the previous frame, writes one row per item
    (or one "blank" row) with the flip time.
    """
    FIELDS = ["trial_num", "frame", "t_flip_s", "unix_time", "item",
              "x_drawn", "y_drawn", "units", "x_px", "y_px", "x_deg_true", "y_deg_true"]

    def __init__(self, win, presenter, geometry):
        self.win, self.presenter, self.geo = win, presenter, geometry
        self.rows = []
        self.trial_num = 0
        self.active = False
        self._frame = 0
        self._last = None
        self._flip = win.flip
        try:
            win.flip = self._logged_flip
        except Exception as e:
            logger.error(f"Target logging disabled, could not wrap flip: {e}")

    def _logged_flip(self, *args, **kwargs):
        out = self._flip(*args, **kwargs)
        if not self.active:
            self.presenter.frame_items = []
            return out
        try:
            t, unix = core.getTime(), time.time()
            items = self.presenter.frame_items
            self.presenter.frame_items = []
            self._frame += 1
            sig = tuple((k, round(x, 4), round(y, 4)) for k, x, y, _ in items)
            if sig != self._last:
                self._last = sig
                base = dict(trial_num=self.trial_num, frame=self._frame, t_flip_s=round(t, 6), unix_time=round(unix, 6))
                if not items:
                    self.rows.append(dict(base, item="blank"))
                for k, x, y, units in items:
                    self.rows.append(dict(base, item=k, **self.geo.describe(x, y, units)))
        except Exception as e:
            logger.error(f"Target logging error: {e}")
        return out

    def start_trial(self, n):
        self.trial_num = n
        self._last = None
        self.active = True

    def trial_summary(self, n, moving=False):      # 11.17.26: added moving (pursuit)
        """
        Onset time and position of the trial's target (first
        frame the dot appears). For a moving target (pursuit)
        only the onset; the path is in the CSV.
        """
        rows = [r for r in self.rows if r["trial_num"] == n]
        dots = [r for r in rows if r["item"] == "dot"]
        out = {"target_rows_logged": len(rows)}
        if dots:
            d = dots[0]
            out.update(target_onset_unix=d["unix_time"], target_onset_t_flip_s=d["t_flip_s"])
            if moving:
                xs = [r["x_deg_true"] for r in dots if r["x_deg_true"] is not None]
                if xs:
                    out.update(target_x_deg_true_min=min(xs), target_x_deg_true_max=max(xs))
            else:
                out.update(target_x_px=d["x_px"], target_y_px=d["y_px"],
                           target_x_deg_true=d["x_deg_true"], target_y_deg_true=d["y_deg_true"])
        return out

    def save(self, folder, trial_type):
        if not self.rows:
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(folder) / f"oculostim_targets_{trial_type.lower()}_{ts}.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.rows)
        return path

# ---- end of 11.11.26 additions ----


# 11.17.26: fix_dur_ms 1000 -> 800, fix_jitter_ms 0 -> 400. The source now uses
# these (it used a hard-coded random 800-1200 ms before), so this keeps the timing.
def get_saccade_config(v = ["8.0", 40, 800, 400, 0, 1000, "random"]) -> dict:
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials": int(v[1]),
        "fix_dur_ms": int(v[2]),
        "fix_jitter_ms": int(v[3]),
        "gap_dur_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "balance": v[6],
    }

# 11.17.26: amplitude 12.0 -> 10.0 (the source now uses this value; it was
# hard-coded to 10 before, so 10 is what every visit so far got).
# 11.17.26: fix_dur_ms 1000 -> 800, fix_jitter_ms 0 -> 400 (see saccade config).
def get_pursuit_config(v = ["horizontal sinusoid", "alternating", 10.0, 10.0, 10.0, 8, 800, 400, 3000]) -> dict:
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

# 11.17.26: fix_dur_ms 1000 -> 800, fix_jitter_ms 0 -> 400 (see saccade config).
def get_fixation_config(v = ["10.0", "5.0", 20, 800, 400, 1000, "random"]) -> dict:
    return {
        "horizontal_ecc": float(v[0]),
        "vertical_ecc": float(v[1]),
        "n_trials": int(v[2]),
        "fix_dur_ms": int(v[3]),
        "fix_jitter_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "order": v[6],
    }

def get_default_config(v = [50.0, 59.0, 2560, 1440, 0, "Saccade Block", "localhost", 9000, True, True, True, False, False, "oculostim", str(Path.home())]) -> dict:
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
        self.session_path = base_vars.get("session_path", "D:\\RawDataLocal")
        print(f"Session path initialized to: {self.session_path}")

        self.trial_type = "Saccade"
        self.trial_data = []
        self.result_data = []

        self.openiris = OpenIrisPythonClient()
        self.set_session_path(self.session_path)    # 11.18.26: was self.openiris.set_recording_path(self.session_path)

        self.target_log = None      # 11.11.26: added (target logging)
        self.cal_attempts = 0       # 11.18.26: added (calibration attempts this session, across blocks)

    # 11.18.26: added - called from __init__ and by StimulusThread
    # when the "init_stimulus|<session folder>" message arrives
    def set_session_path(self, path):
        self.session_path = str(path or "").strip()
        if self.session_path:
            self.openiris.set_recording_path(self.session_path)
            print(f"Session path set to: {self.session_path} (OpenIris records here)")
        else:
            print("No session path yet; OculoStim files will go to the fallback folder if none arrives.")

    # 11.18.26: added - where OculoStim saves its own files
    def _out_dir(self):
        if self.session_path:
            return Path(self.session_path)
        base = Path("D:\\RawDataLocal")
        d = (base if base.exists() else Path.home()) / "oculostim_no_session" / datetime.now().strftime("%Y%m%d")
        d.mkdir(parents=True, exist_ok=True)
        logger.error(f"No session path; saving OculoStim files to {d}")
        return d

    def present_prep(self):
        # 11.18.26: added - re-send the session folder before each block
        if self.session_path:
            self.openiris.set_recording_path(self.session_path)
        self.openiris.start_tracking()
        self.openiris.start_recording()

        cfg = get_default_config()

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

        self.result_data.append({"trial_type": self.trial_type, "trial_data": self.trial_data})
        self.geometry = ScreenGeometry(self.display)            # 11.11.26: added
        self.presenter = LoggingPresenter(self.display)         # 11.11.26: was StimulusPresenter
        self.runner = ExperimentRunner(self.display, self.presenter, None, cfg)

        # 11.11.26: added. Only one flip wrapper per window, even across blocks
        if self.target_log is None:
            self.target_log = TargetLog(self.display, self.presenter, self.geometry)
        else:
            self.target_log.presenter = self.presenter
            self.target_log.geo = self.geometry
        self.target_log.rows = []
        self.target_log.active = False

    def present(self, test=True):
        self.present_prep()
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()

        internal_data = []
        if self.trial_type == "Calibration":
            # 11.11.26: online calibration, falling back to the old
            # offline routine (was: run_gaze_calibration + save JSON here)
            print("Running online gaze calibration...")
            try:
                internal_data = self.run_online_calibration()
            except Exception as e:
                print(f"Online calibration failed ({e}); running the offline calibration instead.")
                logger.error(f"Online calibration failed: {e}")
                internal_data = None

            if internal_data is None:
                internal_data = [self.run_offline_calibration()]

        else:
            n = len(self.trial_data)
            i = 0
            try:                    # 11.11.26: added try/finally so the target log is saved even if a block stops early
                while self.finish.value == 0 and i < n:
                    #self.oi.start()
                    trial = self.trial_data[i]
                    self.runner.stim.set_status(
                        f"Trial {i + 1} / {n}   [{trial['type'].upper()}]")
                    self.target_log.start_trial(i + 1)          # 11.11.26: added
                    record = self.runner.run_trial(i, trial, draw_sync=self.display.draw_patch, flip_sync=self.display.switch_patch)
                    #self.oi.stop()
                    i += 1
                    if record is None:
                        break
                    if isinstance(record, dict):                # 11.11.26: added (11.17.26: pursuit gets onset + range only)
                        record.update(self.target_log.trial_summary(i, moving=trial.get("type") == "pursuit"))
                    internal_data.append(record)
            finally:
                # 11.11.26: added - save the target log
                self.target_log.active = False
                try:
                    path = self.target_log.save(self._out_dir(), self.trial_type)   # 11.18.26: was self.session_path
                    if path:
                        print(f"Saved target positions to {path}")
                except Exception as e:
                    print(f"Failed to save target positions: {e}")
                    logger.error(f"Failed to save target positions: {e}")

        self.result_data.append({"result_data": internal_data})

        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()

        self.openiris.stop_recording()
        self.openiris.stop_tracking()

    # --------------------------------------------------------
    # CALIBRATION - 11.11.26: added (all methods down to
    # run_online_calibration). 11.17.26: calibration dots made
    # to look like the old routine (white ring, black centre,
    # no grid lines or progress text).
    # --------------------------------------------------------

    def _save_json(self, name, obj):
        path = self._out_dir() / name          # 11.18.26: was Path(self.session_path) / name
        try:
            with open(path, "w") as f:
                json.dump(obj, f, indent=2)
            print(f"Saved {path}")
        except Exception as e:
            print(f"Failed to save {path}: {e}")
            logger.error(f"Failed to save {path}: {e}")
        return path

    def run_offline_calibration(self):
        """The old routine: shows the dots, saves their positions, no live gaze."""
        cal_model = run_gaze_calibration(self.display, draw_sync=self.display.draw_patch, flip_sync=self.display.switch_patch)
        if cal_model:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_json(f"oculostim_calibration_{ts}.json", cal_model)
        return {"calibration": "offline", "saved": datetime.now().isoformat()}

    def _aborted(self):
        return self.finish.value != 0 or bool(event.getKeys(["escape"]))

    def _message(self, text, wait_s=None, keys=None):
        """Show text; wait wait_s seconds, or for one of keys (returns the key)."""
        self._msg.text = text
        t_end = None if wait_s is None else core.getTime() + wait_s
        event.clearEvents()
        while True:
            self.display.color = 0.0
            self._msg.draw()
            self.display.draw_patch()
            self.display.flip()
            if self.finish.value != 0:
                return "escape"
            if keys:
                k = event.getKeys(keys)
                if k:
                    return k[0]
            if t_end is not None and core.getTime() >= t_end:
                return None

    def _show_dot(self, x, y, gaze):
        """
        One dot, settle then collect. Returns onset time and
        the gaze samples from the collect period, or None if
        stopped.
        """
        self._ring.pos = (x, y)
        self._dot.pos = (x, y)

        samples = []
        self.display.switch_patch()                 # photodiode: dot on
        t_on = t_unix = None
        t_settle = t_end = None

        while True:
            self.display.color = 0.0
            self._ring.draw()
            self._dot.draw()
            self.display.draw_patch()
            self.display.flip()

            now = core.getTime()
            if t_on is None:
                t_on, t_unix = now, time.time()
                t_settle, t_end = t_on + CAL_SETTLE_S, t_on + CAL_SETTLE_S + CAL_COLLECT_S

            if self._aborted():
                self.display.switch_patch()
                return None

            if now >= t_settle:
                s = gaze.read()
                if s is not None:
                    s["t"] = round(now - t_on, 4)
                    samples.append(s)

            if now >= t_end:
                break

        self.display.switch_patch()                 # photodiode: dot off
        return dict(t_onset_s=round(t_on, 6), onset_unix=round(t_unix, 6), samples=samples)

    @staticmethod
    def _fixation(samples, eye):
        """Median pupil position during the collect period, and tracking coverage."""
        p = "l" if eye == "Left" else "r"
        if not samples:
            return [math.nan, math.nan], 0.0, 0.0
        px = np.array([[s[f"{p}px"], s[f"{p}py"]] for s in samples], dtype=float)
        cr = np.array([[s[f"{p}cx"], s[f"{p}cy"]] for s in samples], dtype=float)
        ok = np.all(np.isfinite(px), axis=1)
        pupil_frac = float(ok.mean())
        cr_frac = float(np.all(np.isfinite(cr), axis=1).mean())
        if pupil_frac < MIN_VALID_FRAC:
            return [math.nan, math.nan], pupil_frac, cr_frac
        return list(np.median(px[ok], axis=0)), pupil_frac, cr_frac

    def _build_cal_stimuli(self):
        win = self.display
        g = self.geometry
        hw = math.degrees(math.atan(g.w_cm / 2 / g.dist_cm))
        hh = math.degrees(math.atan(g.w_cm * g.px_h / g.px_w / 2 / g.dist_cm))

        # Same positions and look as the old routine (white
        # ring, black centre, no grid lines or progress text)
        self._cal_dots = [(hw * (2 * fx - 1), -hh * (2 * fy - 1)) for fx, fy in CAL_FRACS]

        self._ring = visual.Circle(win, radius=0.6, fillColor=None, lineColor="white", lineWidth=2, units="deg")
        self._dot = visual.Circle(win, radius=0.18, fillColor="black", lineColor=None, units="deg")
        self._msg = visual.TextStim(win, text="", pos=(0, 0), color="white", height=0.7, font="Courier New", units="deg", wrapWidth=44, alignText="left")

    def _calibration_attempt(self, gaze, attempt):
        """9 dots, fit, 5 validation dots. Returns the attempt dict, or None if stopped."""
        g = self.geometry
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._message("GAZE CALIBRATION\n\nLook at the centre of each white dot.", wait_s=2.5)

        # ---- 9-point calibration
        cal = []
        for k, (x, y) in enumerate(self._cal_dots):
            r = self._show_dot(x, y, gaze)
            if r is None:
                return None
            r.update(index=k, **g.describe(x, y, "deg"))
            cal.append(r)

        # Same file as the old routine, written now so offline
        # analysis (gazeCalibration.py) finds the run
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_json(f"oculostim_calibration_{ts}.json", [{"tx": x, "ty": y} for x, y in self._cal_dots])

        dots = np.array(self._cal_dots, dtype=float)
        fits = {}

        for eye in ("Left", "Right"):
            fix = [self._fixation(r["samples"], eye) for r in cal]
            px = np.array([f[0] for f in fix], dtype=float)
            good = np.all(np.isfinite(px), axis=1)

            e = dict(fixation_px=[[_r(v, 2) for v in p] for p in px],
                     pupil_tracked=[_r(f[1], 2) for f in fix],
                     cr_tracked=[_r(f[2], 2) for f in fix],
                     dots_used=int(good.sum()), ok=False)

            if good.sum() >= MIN_DOTS_FOR_FIT:
                coef = _affine(px[good], dots[good])
                loo = _leave_one_out(px[good], dots[good])
                e.update(ok=True, coef=[[_r(v, 6) for v in row] for row in coef],
                         loo_h_deg=_r(np.sqrt(np.mean(loo[:, 0] ** 2)), 3),
                         loo_v_deg=_r(np.sqrt(np.mean(loo[:, 1] ** 2)), 3))
            fits[eye] = e

        # ---- validation
        order = random.sample(range(len(VAL_POINTS)), len(VAL_POINTS))
        val = []
        for n, k in enumerate(order):
            x, y = VAL_POINTS[k]
            r = self._show_dot(x, y, gaze)
            if r is None:
                return None
            r.update(index=k, **g.describe(x, y, "deg"))
            val.append(r)

        for eye in ("Left", "Right"):
            e = fits[eye]
            if not e["ok"]:
                continue
            coef = np.array(e["coef"], dtype=float)
            errs = []
            for r in val:
                fx, _, _ = self._fixation(r["samples"], eye)
                if np.all(np.isfinite(fx)):
                    gx, gy = _apply(coef, np.array([fx]))[0]
                    errs.append((gx - r["x_drawn"], gy - r["y_drawn"]))
                else:
                    errs.append((math.nan, math.nan))
            errs = np.array(errs, dtype=float)
            dist = np.hypot(errs[:, 0], errs[:, 1])
            ok = np.isfinite(dist)
            e.update(val_error_deg=[_r(v, 3) for v in dist],
                     val_points_used=int(ok.sum()),
                     val_mean_deg=_r(np.nanmean(dist), 3) if ok.any() else None,
                     val_max_deg=_r(np.nanmax(dist), 3) if ok.any() else None,
                     val_mean_h_deg=_r(np.nanmean(np.abs(errs[:, 0])), 3) if ok.any() else None,
                     val_mean_v_deg=_r(np.nanmean(np.abs(errs[:, 1])), 3) if ok.any() else None)
            e["passed"] = bool(ok.sum() >= 4 and e["val_mean_deg"] <= PASS_MEAN_DEG and e["val_max_deg"] <= PASS_MAX_DEG)

        return dict(attempt=attempt, started=stamp, calibration_file=f"oculostim_calibration_{ts}.json",
                    gaze_source=gaze.source, settle_s=CAL_SETTLE_S, collect_s=CAL_COLLECT_S,
                    screen=dict(width_cm=g.w_cm, distance_cm=g.dist_cm, size_px=[g.px_w, g.px_h]),
                    calibration_dots=cal, validation_dots=val, fits=fits)

    def _results_text(self, a):
        lines = [f"CALIBRATION RESULT (attempt {a['attempt']})", ""]
        for eye in ("Left", "Right"):
            e = a["fits"][eye]
            if not e["ok"]:
                lines.append(f"{eye}: FAILED, pupil tracked on only {e['dots_used']}/9 dots")
                continue
            low_cr = sum(1 for c in e["cr_tracked"] if (c or 0) < MIN_VALID_FRAC)
            lines += [f"{eye}: {'PASS' if e.get('passed') else 'CHECK'}",
                      f"  fit (leave-one-out): {e['loo_h_deg']:.1f} H, {e['loo_v_deg']:.1f} V deg",
                      f"  validation: mean {e['val_mean_deg'] or float('nan'):.1f}, worst {e['val_max_deg'] or float('nan'):.1f} deg"
                      f" ({e['val_points_used']}/5 dots)",
                      f"  pupil lost on {9 - e['dots_used']}/9 dots, corneal reflection lost on {low_cr}/9"]
        # 11.18.26: was "SPACE/ENTER = accept  R = redo  ESC = stop";
        # now an overall verdict and how to redo
        lines += ["", f"Target: mean <= {PASS_MEAN_DEG:.0f} deg, worst <= {PASS_MAX_DEG:.0f} deg", "",
                  "OVERALL: PASS - continue with the tasks" if a.get("passed")
                  else "OVERALL: NOT PASSED - press Calibrate to redo"]
        return "\n".join(lines)

    def run_online_calibration(self):
        """
        Calibrate and validate with live gaze, once. Returns result
        records, or None if no live gaze is available (caller then
        runs the old routine). 11.18.26: was a loop until the
        operator pressed accept; now one attempt per block.
        """
        gaze = LiveGaze(self.openiris)

        # Is live gaze coming in?
        # 11.18.26: waits up to GAZE_WAIT_S (was 1 s), since
        # STARTTRACKING was only just sent and OpenIris replies with
        # zeros until tracking runs. Says which problem it was.
        got, replies = 0, 0
        t_end = core.getTime() + GAZE_WAIT_S
        while core.getTime() < t_end and got < 5:
            s = gaze.read()
            if s is not None:
                replies += 1
            if s and (math.isfinite(s["lpx"]) or math.isfinite(s["rpx"])):
                got += 1
            core.wait(0.02)
        if got < 5:
            why = ("OpenIris answered but no pupil is tracked - check tracking and the eye images"
                   if replies else "no reply from OpenIris - is it running, and is UDP port 9003 open?")
            print(f"No live gaze from OpenIris ({gaze.source}): {why}.")
            logger.error(f"No live gaze from OpenIris ({gaze.source}): {why}")
            gaze.close()
            return None
        print(f"Live gaze from {gaze.source}")

        self._build_cal_stimuli()
        records = []

        # 11.18.26: one attempt per block (was: while loop with
        # accept / redo keys). Attempts are numbered across blocks.
        try:
            if self.finish.value == 0:
                self.cal_attempts += 1
                a = self._calibration_attempt(gaze, self.cal_attempts)
                if a is None:
                    return records

                # 11.18.26: passed = at least one eye met the
                # validation target; result shown for a fixed time
                # (SPACE/ENTER ends it early if the window has focus)
                a["passed"] = any(a["fits"][e].get("passed") for e in ("Left", "Right"))
                a["eyes_passed"] = [e for e in ("Left", "Right") if a["fits"][e].get("passed")]
                text = self._results_text(a)
                print(text)
                self._message(text, wait_s=CAL_RESULT_SHOW_S, keys=["space", "return"])

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._save_json(f"oculostim_onlinecal_{ts}.json", a)

                # Summary for metadata.yaml (no raw samples)
                summary = {k: v for k, v in a.items() if k not in ("calibration_dots", "validation_dots")}
                summary["online_file"] = f"oculostim_onlinecal_{ts}.json"
                summary["calibration_dot_onsets_unix"] = [r["onset_unix"] for r in a["calibration_dots"]]
                summary["validation_dots"] = [{k: r[k] for k in ("index", "onset_unix", "x_drawn", "y_drawn", "x_px", "y_px", "x_deg_true", "y_deg_true")}
                                              for r in a["validation_dots"]]
                records.append(summary)
        finally:
            gaze.close()

        return records

    # ---- end of 11.11.26 additions ----

    def saveMetadata(self, name, sessionFolder):
        return self.result_data

    def update_data(self, trial_data):
        self.trial_type = trial_data[1]
