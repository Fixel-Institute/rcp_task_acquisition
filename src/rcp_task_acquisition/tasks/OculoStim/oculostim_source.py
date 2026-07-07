"""
OculoStim - PsychoPy Edition
Eye movement stimulus controller using PsychoPy for frame-accurate rendering.
"""

from psychopy import visual, core, event, gui, monitors, logging
import csv
import json
import math
import random
import socket
import threading
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog
import os, sys
import clr
import time

from importlib import resources
with resources.path("rcp_task_acquisition.tasks.OculoStim", "OpenIrisRemoteClient.dll") as dll_path:
    clr.AddReference(str(dll_path))
    #unfortunately, this will throw error because DELSYS uses Core CLR but OpenIRIS require legacy CLR.
    #clr.AddReference("System.ServiceModel")

from OpenIris import OpenIrisClient

logging.console.setLevel(logging.WARNING)

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def _parse_eccentricities(s):
    try:
        vals = [float(x.strip()) for x in str(s).split(",") if x.strip()]
        return [v for v in vals if v > 0] or [10.0]
    except ValueError:
        return [10.0]


def choose_folder(start_dir=None):
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(
        title="Choose output folder",
        initialdir=start_dir or str(Path.home())
    )
    root.destroy()
    return folder


# -----------------------------------------------------------------------------
# OPENIRIS UDP CLIENT
# -----------------------------------------------------------------------------

class OpenIrisPythonClient:
    def __init__(self, host="127.0.0.1", port=9000):
        self.host = host
        self.port = port
        self.sock = OpenIrisClient(host, port)

    def start(self):
        self.sock.StartRecording()

    def stop(self):
        self.sock.StopRecording()

    def change_dir(self, path):
        self.sock.ChangeSetting("DataFolder", path)

# -----------------------------------------------------------------------------
# GAZE CALIBRATION MODEL
# -----------------------------------------------------------------------------

def _solve_3x3(M, r):
    A = [list(M[i]) + [r[i]] for i in range(3)]
    for col in range(3):
        max_row = max(range(col, 3), key=lambda i: abs(A[i][col]))
        A[col], A[max_row] = A[max_row], A[col]
        if abs(A[col][col]) < 1e-12:
            return None
        pivot = A[col][col]
        for row in range(col + 1, 3):
            factor = A[row][col] / pivot
            for k in range(col, 4):
                A[row][k] -= factor * A[col][k]
    x = [0.0] * 3
    for i in range(2, -1, -1):
        x[i] = A[i][3]
        for j in range(i + 1, 3):
            x[i] -= A[i][j] * x[j]
        x[i] /= A[i][i]
    return x


class CalibrationModel:
    def __init__(self):
        self._lx = self._ly = None
        self._rx = self._ry = None
        self.rmse_left = None
        self.rmse_right = None
        self.n_points = 0

    @property
    def valid(self):
        return self._lx is not None

    def fit(self, cal_points):
        n = len(cal_points)
        if n < 3:
            return False
        self.n_points = n

        def _fit_axis(ra, rb, t):
            s_a2 = sum(v ** 2 for v in ra)
            s_b2 = sum(v ** 2 for v in rb)
            s_ab = sum(ra[i] * rb[i] for i in range(n))
            s_a = sum(ra)
            s_b = sum(rb)
            s_at = sum(ra[i] * t[i] for i in range(n))
            s_bt = sum(rb[i] * t[i] for i in range(n))
            s_t = sum(t)
            M = [[s_a2, s_ab, s_a],
                 [s_ab, s_b2, s_b],
                 [s_a,  s_b,  n]]
            return _solve_3x3(M, [s_at, s_bt, s_t])

        lx = [p["lx"] for p in cal_points]
        ly = [p["ly"] for p in cal_points]
        rx = [p["rx"] for p in cal_points]
        ry = [p["ry"] for p in cal_points]
        tx = [p["tx"] for p in cal_points]
        ty = [p["ty"] for p in cal_points]

        self._lx = _fit_axis(lx, ly, tx)
        self._ly = _fit_axis(lx, ly, ty)
        self._rx = _fit_axis(rx, ry, tx)
        self._ry = _fit_axis(rx, ry, ty)

        if None in (self._lx, self._ly, self._rx, self._ry):
            self._lx = None
            return False

        def _rmse(cx, cy, ra, rb, tx_, ty_):
            return (sum(
                ((cx[0] * ra[i] + cx[1] * rb[i] + cx[2] - tx_[i]) ** 2 +
                 (cy[0] * ra[i] + cy[1] * rb[i] + cy[2] - ty_[i]) ** 2)
                for i in range(n)) / n) ** 0.5

        self.rmse_left = _rmse(self._lx, self._ly, lx, ly, tx, ty)
        self.rmse_right = _rmse(self._rx, self._ry, rx, ry, tx, ty)
        return True


# -----------------------------------------------------------------------------
# TRIAL BUILDERS
# -----------------------------------------------------------------------------

def build_saccade_trials(cfg):
    n = cfg["n_trials"]
    bal = cfg["balance"]
    directions = []

    while len(directions) < n:

        block = ["left", "right", "up", "down"]
        random.shuffle(block)

        directions.extend(block)

    directions = directions[:n]

    eccs = cfg["eccentricities"]
    trials = []
    for d in directions:
        trials.append({
            "type": "saccade",
            "direction": d,
            "eccentricity": random.choice(eccs),
            "fix_dur_ms": cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "gap_dur_ms": cfg["gap_dur_ms"],
            "stim_dur_ms": cfg["stim_dur_ms"],
        })
    return trials


def build_pursuit_trials(cfg):
    n = cfg["n_trials"]
    mode = cfg["pursuit_mode"]
    direction = cfg["direction"]

    if mode == "diagonal ramp":
        if direction == "alternating":
            dirs = (["left-to-right", "right-to-left"] * math.ceil(n / 2))[:n]
        elif direction == "right-to-left":
            dirs = ["right-to-left"] * n
        else:
            dirs = ["left-to-right"] * n
    else:
        dirs = ["sinusoidal"] * n

    trials = []
    for d in dirs:
        trials.append({
            "type": "pursuit",
            "pursuit_mode": mode,
            "start_ecc": cfg.get("start_ecc", 0.0),
            "amplitude": cfg["amplitude"],
            "speed": cfg["speed"],
            "direction": d,
            "fix_dur_ms": cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "gap_dur_ms": 0,
            "stim_dur_ms": cfg["stim_dur_ms"],
        })
    return trials


def build_fixation_block_trials(cfg):
    h_ecc = cfg["horizontal_ecc"]
    v_ecc = cfg["vertical_ecc"]

    n = cfg["n_trials"]

    combos = [("left", h_ecc),("right", h_ecc),("up", v_ecc),("down", v_ecc)]

    if not combos:
        return []

    if cfg["order"] == "sequential":
        chosen = (combos * math.ceil(n / len(combos)))[:n]
    else:
        chosen = []

        while len(chosen) < n:

            block = combos.copy()
            random.shuffle(block)

            chosen.extend(block)

        chosen = chosen[:n]

    trials = []
    for direction, ecc in chosen:
        trials.append({
            "type": "eccentric_fixation",
            "direction": direction,
            "eccentricity": ecc,
            "fix_dur_ms": cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "stim_dur_ms": cfg["stim_dur_ms"],
        })
    return trials


def build_mixed_trials(s_cfg, p_cfg, fix_n, fix_dur_ms):
    trials = []
    for _ in range(fix_n):
        trials.append({"type": "fixation", "fix_dur_ms": 300, "stim_dur_ms": fix_dur_ms})
    trials += build_saccade_trials(s_cfg)
    trials += build_pursuit_trials(p_cfg)
    random.shuffle(trials)
    return trials


# -----------------------------------------------------------------------------
# STIMULUS PRESENTER
# -----------------------------------------------------------------------------

class StimulusPresenter:
    FIX_SIZE = 0.7
    FIX_WIDTH = 3
    DOT_RAD = 0.4
    SYNC_PX = 40

    def __init__(self, win):
        self.win = win
        self.sync_enabled = False
        self._build()

    def _screen_half_deg(self):
        mon = self.win.monitor
        w_cm = mon.getWidth()
        dist = mon.getDistance()
        px_w, px_h = mon.getSizePix()
        h_cm = w_cm * px_h / px_w
        hw = math.degrees(math.atan(w_cm / 2 / dist))
        hh = math.degrees(math.atan(h_cm / 2 / dist))
        return hw, hh

    def _px_to_deg(self, px):
        mon = self.win.monitor
        w_cm = mon.getWidth()
        dist = mon.getDistance()
        px_w, _ = mon.getSizePix()
        cm = px * w_cm / px_w
        return math.degrees(math.atan(cm / dist)) * 2

    def _build(self):
        w = self.win
        self._fix_h = visual.Line(w, start=(-self.FIX_SIZE, 0), end=(self.FIX_SIZE, 0),
                                  lineWidth=self.FIX_WIDTH, lineColor="black", units="deg")
        self._fix_v = visual.Line(w, start=(0, -self.FIX_SIZE), end=(0, self.FIX_SIZE),
                                  lineWidth=self.FIX_WIDTH, lineColor="black", units="deg")

        self._dot = visual.Circle(w, radius=self.DOT_RAD, fillColor="black",
                                  lineColor=None, units="deg")

        sq_deg = self._px_to_deg(self.SYNC_PX)
        hw, hh = self._screen_half_deg()
        self._sync_sq = visual.Rect(w,
                                    pos=(-hw + sq_deg / 2 + 0.05, hh - sq_deg / 2 - 0.05),
                                    width=sq_deg, height=sq_deg,
                                    fillColor="white", lineColor=None, units="deg")

        self._msg = visual.TextStim(w, text="", pos=(0, 0),
                                    color="white", height=0.8, font="Courier New",
                                    units="deg", wrapWidth=40, alignText="center")

        _, hh2 = self._screen_half_deg()
        self._status = visual.TextStim(w, text="",
                                       pos=(0, hh2 - 0.7), color=[0.3, 0.3, 0.3],
                                       height=0.45, font="Courier New", units="deg", wrapWidth=60)

    def draw_fixation(self, x=0.0, y=0.0, color="black"):
        self._fix_h.pos = (x, y)
        self._fix_v.pos = (x, y)
        self._fix_h.lineColor = color
        self._fix_v.lineColor = color
        self._fix_h.draw()
        self._fix_v.draw()

    def draw_dot(self, x, y, color="black"):
        self._dot.pos = (x, y)
        self._dot.fillColor = color
        self._dot.draw()

    def draw_sync(self):
        if self.sync_enabled:
            self._sync_sq.draw()

    def draw_status(self):
        if self._status.text:
            self._status.draw()

    def show_message(self, text):
        self.win.color = 0.0
        self._msg.text = text
        self._msg.draw()
        self.win.flip()

    def set_status(self, text):
        self._status.text = text


# -----------------------------------------------------------------------------
# GAZE CALIBRATION
# -----------------------------------------------------------------------------

_CAL_FRACS = [
    (0.15, 0.15), (0.50, 0.15), (0.85, 0.15),
    (0.15, 0.50), (0.50, 0.50), (0.85, 0.50),
    (0.15, 0.85), (0.50, 0.85), (0.85, 0.85),
]
_CAL_SETTLE_S = 1.2
_CAL_COLLECT_S = 0.8


def run_gaze_calibration(win, oi):
    mon = win.monitor
    w_cm = mon.getWidth()
    dist = mon.getDistance()
    px_w, px_h = mon.getSizePix()
    h_cm = w_cm * px_h / px_w
    hw = math.degrees(math.atan(w_cm / 2 / dist))
    hh = math.degrees(math.atan(h_cm / 2 / dist))

    targets = [(hw * (2 * fx - 1), -hh * (2 * fy - 1)) for fx, fy in _CAL_FRACS]

    ring = visual.Circle(win, radius=0.6, fillColor=None, lineColor="white", lineWidth=2, units="deg")
    dot = visual.Circle(win, radius=0.18, fillColor="white", lineColor=None, units="deg")

    grid_lines = []
    for fx in (0.15, 0.50, 0.85):
        x = hw * (2 * fx - 1)
        grid_lines.append(visual.Line(win, start=(x, -hh), end=(x, hh),
                                      lineColor=[-0.5, -0.5, -0.5], lineWidth=1, units="deg"))
    for fy in (0.15, 0.50, 0.85):
        y = -hh * (2 * fy - 1)
        grid_lines.append(visual.Line(win, start=(-hw, y), end=(hw, y),
                                      lineColor=[-0.5, -0.5, -0.5], lineWidth=1, units="deg"))

    progress = visual.TextStim(win, text="", pos=(0, -hh + 0.7),
                               color=[0.5, 0.5, 0.5], height=0.45, font="Courier New", units="deg")
    msg_txt = visual.TextStim(win, text="", pos=(0, 0),
                              color="white", height=0.8, font="Courier New",
                              units="deg", wrapWidth=40, alignText="center")

    win.color = 0.0
    msg_txt.text = "GAZE CALIBRATION\n\nFixate each white dot.\n\nPress Escape to cancel."
    msg_txt.draw()
    win.flip()
    core.wait(2.5)
    if event.getKeys(["escape"]):
        return None

    cal_points = []
    n_pts = len(targets)

    for idx, (tx, ty) in enumerate(targets):
        if event.getKeys(["escape"]):
            return None

        settle_end = core.getTime() + _CAL_SETTLE_S
        collect_end = settle_end + _CAL_COLLECT_S
        lx_s, ly_s, rx_s, ry_s = [], [], [], []

        while core.getTime() < collect_end:
            if event.getKeys(["escape"]):
                return None

            win.color = 0.0
            for gl in grid_lines:
                gl.draw()
            ring.pos = (tx, ty)
            dot.pos = (tx, ty)
            ring.draw()
            dot.draw()
            progress.text = f"Point {idx + 1} / {n_pts}"
            progress.draw()
            win.flip()

            if core.getTime() >= settle_end:
                d = oi.get_data()
                if d:
                    try:
                        left = d.get("Left") or d.get("left") or d.get("LeftEye") or d.get("leftEye") or {}
                        right = d.get("Right") or d.get("right") or d.get("RightEye") or d.get("rightEye") or {}

                        def get_xy(eye):
                            pupil = eye.get("Pupil") or {}
                            center = pupil.get("Center") or {}
                            x = eye.get("X", eye.get("x", center.get("X", center.get("x"))))
                            y = eye.get("Y", eye.get("y", center.get("Y", center.get("y"))))
                            return x, y

                        lxv, lyv = get_xy(left)
                        rxv, ryv = get_xy(right)
                        if None not in (lxv, lyv, rxv, ryv):
                            lx_s.append(float(lxv))
                            ly_s.append(float(lyv))
                            rx_s.append(float(rxv))
                            ry_s.append(float(ryv))
                    except Exception:
                        pass

        if len(lx_s) < 3:
            win.color = 0.0
            msg_txt.text = "No gaze data received.\nCheck OpenIris connection."
            msg_txt.draw()
            win.flip()
            core.wait(2.5)
            return None

        cal_points.append({
            "tx": tx, "ty": ty,
            "lx": sum(lx_s) / len(lx_s),
            "ly": sum(ly_s) / len(ly_s),
            "rx": sum(rx_s) / len(rx_s),
            "ry": sum(ry_s) / len(ry_s),
        })

    model = CalibrationModel()
    ok = model.fit(cal_points)

    win.color = 0.0
    if ok:
        msg_txt.text = (f"Calibration complete!\n{model.n_points} points\n"
                        f"RMSE L: {model.rmse_left:.2f} deg   R: {model.rmse_right:.2f} deg")
    else:
        msg_txt.text = "Calibration failed.\nInsufficient or collinear data."
        model = None

    msg_txt.draw()
    win.flip()
    core.wait(2.5)
    return model


# -----------------------------------------------------------------------------
# EXPERIMENT RUNNER
# -----------------------------------------------------------------------------

class ExperimentRunner:
    def __init__(self, win, stim, oi, cfg):
        self.win = win
        self.stim = stim
        self.oi = oi
        self.cfg = cfg
        self.trial_data = []
        self._aborted = False

    def _stamp(self, msg):
        if self.oi and self.oi.connected and self.cfg.get("log_events"):
            self.oi.record_event(msg)

    def run(self, trials):
        n = len(trials)

        if self.oi and self.oi.connected and self.cfg.get("auto_record"):
            self.oi.start_recording()
            core.wait(0.15)
            self._stamp(f"EXPERIMENT_START n={n} mode={self.cfg.get('mode','').replace(' ','_')}")

        for i, trial in enumerate(trials):
            if self._aborted:
                break
            self.stim.set_status(f"Trial {i + 1} / {n}   [{trial['type'].upper()}]")
            record = self._run_trial(i, trial)
            if record is None:
                break
            self.trial_data.append(record)

        self.win.color = 0.0
        self.stim.set_status("")
        self.win.flip()

        if self.oi and self.oi.connected and self.cfg.get("auto_record"):
            tag = "EXPERIMENT_ABORT" if self._aborted else "EXPERIMENT_END"
            self._stamp(f"{tag} trials={len(self.trial_data)}")
            core.wait(0.05)
            self.oi.stop_recording()

    def run_trial(self, i, trial, draw_sync=None, flip_sync=None):
        win = self.win
        stim = self.stim
        ttype = trial["type"]
        n = i + 1
        ecc = trial.get("eccentricity", "")

        fix_dur = random.uniform(0.8, 1.2)
        fix_dur_ms_actual = round(fix_dur * 1000)
        gap_dur = trial.get("gap_dur_ms", 0) / 1000.0
        stim_dur = trial.get("stim_dur_ms", 0) / 1000.0

        resp_key = ""
        rt_ms = ""
        clock = core.Clock()

        event.clearEvents()

        self._stamp(f"FIXATION_ON trial={n:03d} type={ttype.upper()}")
        clock.reset()
        first_fix_frame = True
        while clock.getTime() < fix_dur:
            win.color = 0.0
            stim.draw_fixation()
            if first_fix_frame:
                flip_sync()
                draw_sync()
                first_fix_frame = False
            stim.draw_status()
            win.flip()
            keys = event.getKeys(["escape", "space"])
            if "escape" in keys:
                self._aborted = True
                return None
            if "space" in keys and not resp_key:
                resp_key = "space"
                rt_ms = round(clock.getTime() * 1000, 2)

        if gap_dur > 0:
            self._stamp(f"GAP_ON trial={n:03d}")
            clock.reset()
            while clock.getTime() < gap_dur:
                win.color = 0.0
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        self._stamp(f"BeforeStimON trial={n:03d} type={ttype.upper()}")
        actual_onset = 0.0

        if ttype == "fixation":
            clock.reset()
            win.color = 0.0
            stim.draw_fixation()
            flip_sync()
            draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_fixation()
                draw_sync()
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "saccade":
            direction = trial["direction"]
            ecc = trial["eccentricity"]
            if direction == "left":
                tx, ty = -ecc, 0
            elif direction == "right":
                tx, ty = ecc, 0
            elif direction == "up":
                tx, ty = 0, ecc
            else:  # down
                tx, ty = 0, -ecc
            self._stamp(f"BeforeStimON trial={n:03d} SACCADE direction={direction} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_dot(tx, ty)
            flip_sync()
            draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_dot(tx, ty)
                draw_sync()
                stim.draw_status()
                win.flip()
                keys = event.getKeys(["escape", "space"])
                if "escape" in keys:
                    self._aborted = True
                    return None
                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms = round((clock.getTime() - actual_onset) * 1000, 2)

        elif ttype == "eccentric_fixation":
            direction = trial["direction"]
                
            ecc = trial["eccentricity"]
            if direction == "left":
                tx, ty = -ecc, 0
            elif direction == "right":
                tx, ty = ecc, 0
            elif direction == "up":
                tx, ty = 0, ecc
            else:  # down
                tx, ty = 0, -ecc

            # hold fixation target for 5-10 seconds
            stim_dur = random.uniform(5.0, 10.0)
            stim_dur_ms_actual = round(stim_dur * 1000)

            self._stamp(f"BeforeStimON trial={n:03d} ECC_FIX direction={direction} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_dot(tx, ty)
            flip_sync()
            draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_dot(tx, ty)
                draw_sync()
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "pursuit":
            amp = trial["amplitude"]
            speed = trial["speed"]
            mode = trial["pursuit_mode"]
            direc = trial["direction"]
            start_ecc = trial.get("start_ecc", 10.0)

            self._stamp(
                f"BeforeStimON trial={n:03d} "
                f"PURSUIT mode={mode} dir={direc}"
            )

            # --------------------------------------------------
            # DIAGONAL RAMP
            # --------------------------------------------------
            if mode == "diagonal ramp":

                if direc == "right-to-left":
                    x0 = start_ecc
                    x1 = -start_ecc
                else:
                    x0 = -start_ecc
                    x1 = start_ecc

                # start below center
                y0 = -amp

                dx = x1 - x0
                dy = 2 * amp

                path_len = math.sqrt(dx*dx + dy*dy)

                ux = dx / path_len
                uy = dy / path_len

                t_end = min(stim_dur, path_len / speed)

                start_pos = (x0, y0)

            # --------------------------------------------------
            # HORIZONTAL SINUSOID
            # --------------------------------------------------
            else:

                amp = 10.0
                freq = 0.4
                fixation_dur = 1.0
                ramp_dur = 1.0

                cycles = 4
                pursuit_dur = cycles / freq   # 10 seconds

                intertrial_dur = 1.0

                clock.reset()
                actual_onset = 0.0

                ramp_dur = 1.0

                fix_clock = core.Clock()
                
                flip_sync()
                draw_sync()

                start_dir = "right" if (i % 2 == 0) else "left"

                while fix_clock.getTime() < fixation_dur:

                    win.color = 0.0
                    stim.draw_fixation()
                    draw_sync()
                    stim.draw_status()
                    win.flip()

                    if "escape" in event.getKeys(["escape"]):
                        self._aborted = True
                        return None

                clock.reset()
                flip_sync()
                draw_sync()

                while clock.getTime() < (ramp_dur + pursuit_dur):

                    t = clock.getTime()

                    if t < ramp_dur:
                        envelope = 0.5 * (
                            1.0 - math.cos(math.pi * t / ramp_dur)
                        )
                    else:
                        envelope = 1.0

                    sign = 1.0 if start_dir == "right" else -1.0

                    x = sign * amp * envelope * math.sin(
                        2 * math.pi * freq * t
                    )

                    win.color = 0.0
                    stim.draw_dot(x, 0)
                    flip_sync()
                    draw_sync()
                    stim.draw_status()
                    win.flip()

                    keys = event.getKeys(["escape", "space"])

                    if "escape" in keys:
                        self._aborted = True
                        return None

                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms = round((clock.getTime() - actual_onset) * 1000,2)

        else:
            return None

        actual_dur_ms = round(clock.getTime() * 1000, 2)
        self._stamp(f"STIM_OFF trial={n:03d}")

        return {
            "trial_num": n,
            "type": ttype,
            "direction": trial.get("direction", ""),
            "eccentricity_deg": ecc if ecc is not None else "",
            "pursuit_start_ecc_deg": trial.get("start_ecc", ""),
            "amplitude_deg": trial.get("amplitude", ""),
            "speed_deg_s": trial.get("speed", ""),
            "pursuit_mode": trial.get("pursuit_mode", ""),
            "fix_dur_ms": fix_dur_ms_actual,
            "gap_dur_ms": trial.get("gap_dur_ms", 0),
            "stim_dur_ms": stim_dur_ms_actual if ttype == "eccentric_fixation"
               else trial.get("stim_dur_ms", 0),
            "actual_dur_ms": actual_dur_ms,
            "response_key": resp_key,
            "rt_ms": rt_ms,
            "timestamp": datetime.now().isoformat(),
        }

    def _run_trial(self, i, trial):
        win = self.win
        stim = self.stim
        ttype = trial["type"]
        n = i + 1
        ecc = trial.get("eccentricity", "")

        fix_dur = random.uniform(0.8, 1.2)
        fix_dur_ms_actual = round(fix_dur * 1000)
        gap_dur = trial.get("gap_dur_ms", 0) / 1000.0
        stim_dur = trial.get("stim_dur_ms", 0) / 1000.0

        resp_key = ""
        rt_ms = ""
        clock = core.Clock()

        event.clearEvents()

        self._stamp(f"FIXATION_ON trial={n:03d} type={ttype.upper()}")
        clock.reset()
        first_fix_frame = True
        while clock.getTime() < fix_dur:
            win.color = 0.0
            stim.draw_fixation()
            if first_fix_frame:
                stim.draw_sync()
                first_fix_frame = False
            stim.draw_status()
            win.flip()
            keys = event.getKeys(["escape", "space"])
            if "escape" in keys:
                self._aborted = True
                return None
            if "space" in keys and not resp_key:
                resp_key = "space"
                rt_ms = round(clock.getTime() * 1000, 2)

        if gap_dur > 0:
            self._stamp(f"GAP_ON trial={n:03d}")
            clock.reset()
            while clock.getTime() < gap_dur:
                win.color = 0.0
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        self._stamp(f"BeforeStimON trial={n:03d} type={ttype.upper()}")
        actual_onset = 0.0

        if ttype == "fixation":
            clock.reset()
            win.color = 0.0
            stim.draw_fixation()
            stim.draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_fixation()
                stim.draw_sync()
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "saccade":
            direction = trial["direction"]
            ecc = trial["eccentricity"]
            if direction == "left":
                tx, ty = -ecc, 0
            elif direction == "right":
                tx, ty = ecc, 0
            elif direction == "up":
                tx, ty = 0, ecc
            else:  # down
                tx, ty = 0, -ecc
            self._stamp(f"BeforeStimON trial={n:03d} SACCADE direction={direction} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_dot(tx, ty)
            stim.draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_dot(tx, ty)
                stim.draw_sync()
                stim.draw_status()
                win.flip()
                keys = event.getKeys(["escape", "space"])
                if "escape" in keys:
                    self._aborted = True
                    return None
                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms = round((clock.getTime() - actual_onset) * 1000, 2)

        elif ttype == "eccentric_fixation":
            direction = trial["direction"]
                
            ecc = trial["eccentricity"]
            if direction == "left":
                tx, ty = -ecc, 0
            elif direction == "right":
                tx, ty = ecc, 0
            elif direction == "up":
                tx, ty = 0, ecc
            else:  # down
                tx, ty = 0, -ecc

            # hold fixation target for 5-10 seconds
            stim_dur = random.uniform(5.0, 10.0)
            stim_dur_ms_actual = round(stim_dur * 1000)

            self._stamp(f"BeforeStimON trial={n:03d} ECC_FIX direction={direction} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_dot(tx, ty)
            stim.draw_sync()
            stim.draw_status()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_dot(tx, ty)
                stim.draw_sync()
                stim.draw_status()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "pursuit":
            amp = trial["amplitude"]
            speed = trial["speed"]
            mode = trial["pursuit_mode"]
            direc = trial["direction"]
            start_ecc = trial.get("start_ecc", 10.0)

            self._stamp(
                f"BeforeStimON trial={n:03d} "
                f"PURSUIT mode={mode} dir={direc}"
            )

            # --------------------------------------------------
            # DIAGONAL RAMP
            # --------------------------------------------------
            if mode == "diagonal ramp":

                if direc == "right-to-left":
                    x0 = start_ecc
                    x1 = -start_ecc
                else:
                    x0 = -start_ecc
                    x1 = start_ecc

                # start below center
                y0 = -amp

                dx = x1 - x0
                dy = 2 * amp

                path_len = math.sqrt(dx*dx + dy*dy)

                ux = dx / path_len
                uy = dy / path_len

                t_end = min(stim_dur, path_len / speed)

                start_pos = (x0, y0)

            # --------------------------------------------------
            # HORIZONTAL SINUSOID
            # --------------------------------------------------
            else:

                amp = 10.0
                freq = 0.4
                fixation_dur = 1.0
                ramp_dur = 1.0

                cycles = 4
                pursuit_dur = cycles / freq   # 10 seconds

                intertrial_dur = 1.0

                clock.reset()
                actual_onset = 0.0

                ramp_dur = 1.0

                fix_clock = core.Clock()

                start_dir = "right" if (i % 2 == 0) else "left"

                while fix_clock.getTime() < fixation_dur:

                    win.color = 0.0
                    stim.draw_fixation()
                    stim.draw_sync()
                    stim.draw_status()
                    win.flip()

                    if "escape" in event.getKeys(["escape"]):
                        self._aborted = True
                        return None

                clock.reset()

                while clock.getTime() < (ramp_dur + pursuit_dur):

                    t = clock.getTime()

                    if t < ramp_dur:
                        envelope = 0.5 * (
                            1.0 - math.cos(math.pi * t / ramp_dur)
                        )
                    else:
                        envelope = 1.0

                    sign = 1.0 if start_dir == "right" else -1.0

                    x = sign * amp * envelope * math.sin(
                        2 * math.pi * freq * t
                    )

                    win.color = 0.0
                    stim.draw_dot(x, 0)
                    stim.draw_sync()
                    stim.draw_status()
                    win.flip()

                    keys = event.getKeys(["escape", "space"])

                    if "escape" in keys:
                        self._aborted = True
                        return None

                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms = round((clock.getTime() - actual_onset) * 1000,2)

        else:
            return None

        actual_dur_ms = round(clock.getTime() * 1000, 2)
        self._stamp(f"STIM_OFF trial={n:03d}")

        return {
            "trial_num": n,
            "type": ttype,
            "direction": trial.get("direction", ""),
            "eccentricity_deg": ecc if ecc is not None else "",
            "pursuit_start_ecc_deg": trial.get("start_ecc", ""),
            "amplitude_deg": trial.get("amplitude", ""),
            "speed_deg_s": trial.get("speed", ""),
            "pursuit_mode": trial.get("pursuit_mode", ""),
            "fix_dur_ms": fix_dur_ms_actual,
            "gap_dur_ms": trial.get("gap_dur_ms", 0),
            "stim_dur_ms": stim_dur_ms_actual if ttype == "eccentric_fixation"
               else trial.get("stim_dur_ms", 0),
            "actual_dur_ms": actual_dur_ms,
            "response_key": resp_key,
            "rt_ms": rt_ms,
            "timestamp": datetime.now().isoformat(),
        }

    def export_csv(self, path):
        if not self.trial_data:
            return False
        fields = list(self.trial_data[0].keys())
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.trial_data)
        return True


# -----------------------------------------------------------------------------
# CONFIGURATION DIALOGS
# -----------------------------------------------------------------------------

def _dlg_screen():
    d = gui.Dlg(title="OculoStim - Setup")
    d.addText("SCREEN")
    d.addField("Viewing distance (cm):", 57.0)
    d.addField("Screen width (cm):", 52.7)
    d.addField("Resolution (px) - width:", 1920)
    d.addField("Resolution (px) - height:", 1080)
    d.addField("Screen number (0 = primary):", 0)
    d.addText("")
    d.addText("PARADIGM")
    d.addField("Mode:", choices=["Saccade Block", "Pursuit Block", "Fixation Block", "Mixed Block"])
    d.addText("")
    d.addText("OPENIRIS")
    d.addField("Host:", "127.0.0.1")
    d.addField("Port:", 9003)
    d.addField("Connect to OpenIris?", True)
    d.addField("Auto-record with experiment?", True)
    d.addField("Log trial events?", True)
    d.addField("Calibrate gaze?", False)
    d.addField("Photodiode sync square?", False)
    d.addText("")
    d.addText("OUTPUT")
    d.addField("Session name:", "oculostim")
    d.addField("Output folder:", str(Path.home()))
    d.show()
    if not d.OK:
        return None
    v = d.data
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


def _dlg_saccade():
    d = gui.Dlg(title="Saccade Block")
    d.addField("Eccentricity - deg, comma-separated:", "10.0")
    d.addField("# Trials:", 40)
    d.addField("Fixation duration (ms):", 1000)
    d.addField("Fix. jitter +/- (ms):", 0)
    d.addField("Gap duration (ms):", 0)
    d.addField("Target duration (ms):", 1000)
    d.addField("Balance:", choices=["interleaved", "random", "left only", "right only"])
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials": int(v[1]),
        "fix_dur_ms": int(v[2]),
        "fix_jitter_ms": int(v[3]),
        "gap_dur_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "balance": v[6],
    }


def _dlg_pursuit():
    d = gui.Dlg(title="Pursuit Block")
    d.addField("Pursuit stimulus:", choices=[ "horizontal sinusoid", "diagonal ramp"])
    d.addField("Ramp direction:", choices=["alternating", "left-to-right", "right-to-left"])
    d.addField("Start eccentricity (deg):", 10.0)
    d.addField("Amplitude +/- (deg):", 12.0)
    d.addField("Speed (deg/s)  [ramp: constant velocity; sine: peak velocity]:", 10.0)
    d.addField("# Trials:", 8)
    d.addField("Fixation duration (ms):", 1000)
    d.addField("Fix. jitter +/- (ms):", 0)
    d.addField("Sweep duration (ms):", 3000)
    d.show()
    if not d.OK:
        return None
    v = d.data
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


def _dlg_fixation():
    d = gui.Dlg(title="Fixation Block")
    d.addField("Horizontal eccentricity (deg):", 20.0)
    d.addField("Vertical eccentricity (deg):", 15.0)
    d.addField("# Trials:", 20)
    d.addField("Central fixation duration (ms):", 1000)
    d.addField("Fix. jitter +/- (ms):", 0)
    d.addField("Eccentric fixation duration (ms):", 1000)
    d.addField("Order:", choices=["random", "sequential"])
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "horizontal_ecc": float(v[0]),
        "vertical_ecc": float(v[1]),
        "n_trials": int(v[2]),
        "fix_dur_ms": int(v[3]),
        "fix_jitter_ms": int(v[4]),
        "stim_dur_ms": int(v[5]),
        "order": v[6],
    }


def _dlg_mixed():
    d = gui.Dlg(title="Mixed Block - Fixation-only Trials")
    d.addText("Saccade and Pursuit parameters were set in the previous dialogs.")
    d.addField("# Fixation-only trials:", 5)
    d.addField("Fixation-only duration (ms):", 2000)
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {"fix_n": int(v[0]), "fix_dur_ms": int(v[1])}


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    cfg = _dlg_screen()
    if cfg is None:
        return

    if not cfg["output_folder"].strip():
        picked = choose_folder()
        if not picked:
            return
        cfg["output_folder"] = picked

    mode = cfg["mode"]

    s_cfg = p_cfg = f_cfg = m_cfg = None

    if mode in ("Saccade Block", "Mixed Block"):
        s_cfg = _dlg_saccade()
        if s_cfg is None:
            return

    if mode in ("Pursuit Block", "Mixed Block"):
        p_cfg = _dlg_pursuit()
        if p_cfg is None:
            return

    if mode == "Fixation Block":
        f_cfg = _dlg_fixation()
        if f_cfg is None:
            return

    if mode == "Mixed Block":
        m_cfg = _dlg_mixed()
        if m_cfg is None:
            return

    if mode == "Saccade Block":
        trials = build_saccade_trials(s_cfg)
    elif mode == "Pursuit Block":
        trials = build_pursuit_trials(p_cfg)
    elif mode == "Fixation Block":
        trials = build_fixation_block_trials(f_cfg)
    else:
        trials = build_mixed_trials(s_cfg, p_cfg, m_cfg["fix_n"], m_cfg["fix_dur_ms"])

    if not trials:
        d = gui.Dlg(title="OculoStim")
        d.addText("No trials were generated. Check your parameters.")
        d.show()
        return

    oi = OpenIrisClient(cfg["oi_host"], cfg["oi_port"])

    if cfg["oi_connect"]:
        ok = oi.connect()
        if not ok:
            d = gui.Dlg(title="OpenIris - Connection Failed")
            d.addText(f"Could not reach OpenIris at {cfg['oi_host']}:{cfg['oi_port']}.")
            d.addText("Continuing without OpenIris.")
            d.show()

    mon = monitors.Monitor("oculostim", width=cfg["screen_w_cm"], distance=cfg["screen_dist"])
    mon.setSizePix((1920, 1080))

    win = visual.Window(
        size=(1920, 1080),
        screen=1,
        units='pix',
        gammaErrorPolicy='warn',
        useFBO=True,
        color=-1,
        fullscr=True,
        waitBlanking=True,
        winType="pyglet",
        infoMsg=""
    )
    win.monitor = mon
    win.mouseVisible = False

    stim = StimulusPresenter(win)
    stim.sync_enabled = cfg["sync_sq"]

    cal_model = None
    if oi.connected and cfg["do_calibrate"]:
        cal_model = run_gaze_calibration(win, oi)
        if cal_model and cal_model.valid:
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cal_path = Path(cfg["output_folder"]) / f"oculostim_{cfg['session']}_calibration_{ts}.json"
                cal_data = {
                    "session": cfg["session"],
                    "timestamp": ts,
                    "n_points": cal_model.n_points,
                    "rmse_left": cal_model.rmse_left,
                    "rmse_right": cal_model.rmse_right,
                    "left_eye": {"x_coeffs": cal_model._lx, "y_coeffs": cal_model._ly},
                    "right_eye": {"x_coeffs": cal_model._rx, "y_coeffs": cal_model._ry},
                }
                with open(cal_path, "w") as f:
                    json.dump(cal_data, f, indent=2)
            except Exception as e:
                print(f"[Calibration save failed] {e}")

    cfg["mode"] = mode
    runner = ExperimentRunner(win, stim, oi, cfg)

    stim.show_message(f"OculoStim\n\n{mode}  -  {len(trials)} trials\n\nPress any key to begin.\nEscape aborts at any time.")
    event.waitKeys()

    runner.run(trials)

    out_path = Path(cfg["output_folder"]) / f"{cfg['session']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    saved = runner.export_csv(out_path)

    win.close()
    oi.disconnect()

    d = gui.Dlg(title="OculoStim - Complete")
    d.addText(f"Block complete: {len(runner.trial_data)} / {len(trials)} trials")
    if saved:
        d.addText(f"Saved: {out_path}")
    d.show()

def test_openiris():
    try:
        oi = OpenIrisPythonClient("localhost", 9000)
    except Exception as e:
        print(f"OpenIrisPythonClient initialization failed: {e}")
        return 
    
    oi.change_dir("D:\\RawDataLocal\\20260707\\unitUFL\\session004 (oculostim_task)")
    oi.start()
    time.sleep(5)
    oi.stop()

if __name__ == "__main__":
    test_openiris()
