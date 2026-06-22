"""
OculoStim — PsychoPy Edition
=============================
Eye movement stimulus controller using PsychoPy for frame-accurate rendering.

Stimulus types:
  • Fixation Cross        — central fixation point
  • Saccade               — fixation → eccentric dot (configurable eccentricities)
  • Smooth Pursuit        — horizontally moving dot (configurable speed/amplitude)
  • Eccentric Fixation    — fixation cross at configurable eccentricities

Paradigm blocks:
  • Saccade Block         — interleaved left/right saccade trials
  • Pursuit Block         — continuous smooth pursuit sweeps
  • Fixation Block        — eccentric fixation
  • Mixed Block           — fixation + saccade + pursuit interleaved

OpenIris integration (UDP, port 9003 by default):
  • Auto start/stop recording with experiment
  • BeforeStimON / AfterStimON event bracketing at every stimulus flip
  • 9-point affine gaze calibration

Requirements: Python 3.8+, PsychoPy 2023+
Run: python oculostim.py
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

logging.console.setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# OPENIRIS UDP CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class OpenIrisClient:
    """
    Lightweight UDP client for the OpenIris eye-tracker remote interface.
    Port is ServiceListeningPort + 3 (default 9003).

    Supported commands:
      STARTRECORDING   STOPRECORDING   GETDATA   WAITFORDATA
      RECORDEVENT|<msg>   CALIBRATION|<data>   TESEMPTY
    """

    _NO_RESPONSE = {"STARTRECORDING", "STOPRECORDING"}

    def __init__(self, host="127.0.0.1", port=9003, timeout=2.0):
        self.host    = host
        self.port    = port
        self.timeout = timeout
        self._sock   = None
        self._lock   = threading.Lock()

    @property
    def connected(self):
        return self._sock is not None

    def connect(self):
        """Ping OpenIris with TESEMPTY. Returns True on 0x44 ('D') response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            sock.sendto(b"TESEMPTY", (self.host, self.port))
            data, _ = sock.recvfrom(256)
            if data and data[0] == 68:
                self._sock = sock
                return True
            sock.close()
        except Exception:
            pass
        return False

    def disconnect(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None

    def _send(self, command):
        if not self._sock:
            return None
        cmd_upper = command.split("|")[0].strip().upper()
        try:
            with self._lock:
                self._sock.sendto(command.encode("ascii"), (self.host, self.port))
                if cmd_upper in self._NO_RESPONSE:
                    return b""
                data, _ = self._sock.recvfrom(4096)
                return data
        except (socket.timeout, Exception):
            return None

    def start_recording(self):
        return self._send("STARTRECORDING") is not None

    def stop_recording(self):
        return self._send("STOPRECORDING") is not None

    def record_event(self, message):
        """Stamp a text event. Returns camera frame number or None."""
        data = self._send(f"RECORDEVENT|{message}")
        if data:
            try:
                return int(data.decode("ascii").strip())
            except (ValueError, UnicodeDecodeError):
                return None
        return None

    def get_data(self):
        """Return latest eye-data frame as dict, or None."""
        data = self._send("GETDATA")
        if data:
            try:
                return json.loads(data.decode("ascii"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GAZE CALIBRATION MODEL
# ─────────────────────────────────────────────────────────────────────────────

def _solve_3x3(M, r):
    """Solve 3×3 linear system M @ x = r via Gaussian elimination (partial pivot).
    Returns [x0, x1, x2] or None if singular."""
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
    """
    Affine gaze calibration: maps raw OpenIris (X, Y) to visual degrees.

    Per-eye 2D affine transform fit via least-squares over N ≥ 3 points:
      gaze_x_deg = a·raw_x + b·raw_y + c
      gaze_y_deg = d·raw_x + e·raw_y + f
    """

    def __init__(self):
        self._lx = self._ly = None
        self._rx = self._ry = None
        self.rmse_left  = None
        self.rmse_right = None
        self.n_points   = 0

    @property
    def valid(self):
        return self._lx is not None

    def fit(self, cal_points):
        """
        Fit from list of dicts: {tx, ty (deg), lx, ly, rx, ry (raw gaze)}.
        Returns True on success.
        """
        n = len(cal_points)
        if n < 3:
            return False
        self.n_points = n

        def _fit_axis(ra, rb, t):
            s_a2 = sum(v**2 for v in ra)
            s_b2 = sum(v**2 for v in rb)
            s_ab = sum(ra[i] * rb[i] for i in range(n))
            s_a  = sum(ra)
            s_b  = sum(rb)
            s_at = sum(ra[i] * t[i] for i in range(n))
            s_bt = sum(rb[i] * t[i] for i in range(n))
            s_t  = sum(t)
            M = [[s_a2, s_ab, s_a],
                 [s_ab, s_b2, s_b],
                 [s_a,  s_b,  n  ]]
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
                ((cx[0]*ra[i] + cx[1]*rb[i] + cx[2] - tx_[i])**2 +
                 (cy[0]*ra[i] + cy[1]*rb[i] + cy[2] - ty_[i])**2)
                for i in range(n)) / n) ** 0.5

        self.rmse_left  = _rmse(self._lx, self._ly, lx, ly, tx, ty)
        self.rmse_right = _rmse(self._rx, self._ry, rx, ry, tx, ty)
        return True

    def apply_left(self, raw_x, raw_y):
        """Map raw left-eye values to (x_deg, y_deg) from screen centre."""
        if not self.valid:
            return None, None
        return (self._lx[0]*raw_x + self._lx[1]*raw_y + self._lx[2],
                self._ly[0]*raw_x + self._ly[1]*raw_y + self._ly[2])

    def apply_right(self, raw_x, raw_y):
        if not self.valid:
            return None, None
        return (self._rx[0]*raw_x + self._rx[1]*raw_y + self._rx[2],
                self._ry[0]*raw_x + self._ry[1]*raw_y + self._ry[2])


# ─────────────────────────────────────────────────────────────────────────────
# TRIAL BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_saccade_trials(cfg):
    n   = cfg["n_trials"]
    bal = cfg["balance"]
    if bal == "interleaved":
        sides = (["left", "right"] * math.ceil(n / 2))[:n]
    elif bal == "left only":
        sides = ["left"] * n
    elif bal == "right only":
        sides = ["right"] * n
    else:
        sides = [random.choice(["left", "right"]) for _ in range(n)]

    eccs   = cfg["eccentricities"]
    trials = []
    for s in sides:
        trials.append({
            "type":         "saccade",
            "side":         s,
            "eccentricity": random.choice(eccs),
            "fix_dur_ms":   cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "gap_dur_ms":   cfg["gap_dur_ms"],
            "stim_dur_ms":  cfg["stim_dur_ms"],
        })
    return trials


def build_pursuit_trials(cfg):
    n = cfg["n_trials"]
    d = cfg["direction"]
    if d == "alternating":
        dirs = (["left-to-right", "right-to-left"] * math.ceil(n / 2))[:n]
    elif d == "oscillate":
        dirs = ["oscillate"] * n
    elif d == "right-to-left":
        dirs = ["right-to-left"] * n
    else:
        dirs = ["left-to-right"] * n

    trials = []
    for direction in dirs:
        trials.append({
            "type":        "pursuit",
            "amplitude":   cfg["amplitude"],
            "speed":       cfg["speed"],
            "direction":   direction,
            "fix_dur_ms":  cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "gap_dur_ms":  0,
            "stim_dur_ms": cfg["stim_dur_ms"],
        })
    return trials


def build_fixation_block_trials(cfg):
    eccs      = cfg["eccentricities"]
    sides_opt = cfg["sides"]
    n         = cfg["n_trials"]

    combos = []
    for ecc in eccs:
        if sides_opt == "left only":
            combos.append(("left", ecc))
        elif sides_opt == "right only":
            combos.append(("right", ecc))
        else:
            combos += [("left", ecc), ("right", ecc)]

    if not combos:
        return []

    if cfg["order"] == "sequential":
        chosen = (combos * math.ceil(n / len(combos)))[:n]
    else:
        chosen = [random.choice(combos) for _ in range(n)]

    trials = []
    for side, ecc in chosen:
        trials.append({
            "type":         "eccentric_fixation",
            "side":         side,
            "eccentricity": ecc,
            "fix_dur_ms":   cfg["fix_dur_ms"] + random.randint(0, cfg["fix_jitter_ms"]),
            "stim_dur_ms":  cfg["stim_dur_ms"],
        })
    return trials


def build_mixed_trials(s_cfg, p_cfg, fix_n, fix_dur_ms):
    trials = []
    for _ in range(fix_n):
        trials.append({"type": "fixation", "fix_dur_ms": 300,
                        "stim_dur_ms": fix_dur_ms})
    trials += build_saccade_trials(s_cfg)
    trials += build_pursuit_trials(p_cfg)
    random.shuffle(trials)
    return trials


# ─────────────────────────────────────────────────────────────────────────────
# STIMULUS PRESENTER
# ─────────────────────────────────────────────────────────────────────────────

class StimulusPresenter:
    """
    Manages PsychoPy stimulus objects.  All sizes and positions are in
    degrees of visual angle (matching win.units = 'deg').
    """

    FIX_SIZE  = 100    # fixation cross half-length (pixel)
    FIX_WIDTH = 3      # line width (px)
    DOT_RAD   = 100    # target dot radius (pixel)
    SYNC_PX   = 40     # photodiode sync square side (px)

    def __init__(self, win, sync=None):
        self.win          = win
        self.sync_enabled = True if sync else False
        self.sync         = sync
        self._build()

    def _screen_half_deg(self):
        mon  = self.win.monitor
        w_cm = mon.getWidth()
        dist = mon.getDistance()
        px_w, px_h = mon.getSizePix()
        h_cm = w_cm * px_h / px_w
        hw = math.degrees(math.atan(w_cm / 2 / dist))
        hh = math.degrees(math.atan(h_cm / 2 / dist))
        return hw, hh

    def _px_to_deg(self, px):
        mon  = self.win.monitor
        w_cm = mon.getWidth()
        dist = mon.getDistance()
        px_w, _ = mon.getSizePix()
        cm = px * w_cm / px_w
        return math.degrees(math.atan(cm / dist)) * 2

    def _build(self):
        w = self.win

        self._fix_h = visual.Line(w,
            start=(-self.FIX_SIZE, 0), end=(self.FIX_SIZE, 0),
            lineWidth=self.FIX_WIDTH, lineColor="black", units="pix")
        self._fix_v = visual.Line(w,
            start=(0, -self.FIX_SIZE), end=(0, self.FIX_SIZE),
            lineWidth=self.FIX_WIDTH, lineColor="black", units="pix")

        self._dot = visual.Circle(w,
            radius=self.DOT_RAD, fillColor="black",
            lineColor=None, units="pix")

        self._pursuit_h = visual.Line(w,
            lineColor=[0.2, 0.2, 0.2], lineWidth=1, units="pix")
        self._pursuit_ck = visual.Line(w,
            lineColor=[0.2, 0.2, 0.2], lineWidth=1, units="pix")

        self._msg = visual.TextStim(w, text="", pos=(0, 0),
            color="white", height=0.8, font="Courier New",
            units="pix", wrapWidth=40, alignText="center")

        self._status = visual.TextStim(w, text="",
            pos=(0, 450 - 0.7), color=[0.3, 0.3, 0.3],
            height=0.45, font="Courier New", units="pix", wrapWidth=60)

    # ── Draw calls ────────────────────────────────────────────────────────────
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

    def draw_pursuit_guide(self, amplitude):
        half = amplitude + 0.7
        self._pursuit_h.start  = (-half, 0)
        self._pursuit_h.end    = ( half, 0)
        self._pursuit_ck.start = (0, -0.3)
        self._pursuit_ck.end   = (0,  0.3)
        self._pursuit_h.draw()
        self._pursuit_ck.draw()

    def draw_status(self):
        if self._status.text:
            self._status.draw()

    def show_message(self, text):
        """Clear screen, draw centred message, flip."""
        self.win.color = 0.0
        self._msg.text = text
        self._msg.draw()
        self.win.flip()

    def set_status(self, text):
        self._status.text = text


# ─────────────────────────────────────────────────────────────────────────────
# GAZE CALIBRATION  (9-point, PsychoPy-native)
# ─────────────────────────────────────────────────────────────────────────────

# 3×3 grid target positions as fractions of screen (left→right, top→bottom)
_CAL_FRACS = [
    (0.15, 0.15), (0.50, 0.15), (0.85, 0.15),
    (0.15, 0.50), (0.50, 0.50), (0.85, 0.50),
    (0.15, 0.85), (0.50, 0.85), (0.85, 0.85),
]
_CAL_SETTLE_S  = 1.2
_CAL_COLLECT_S = 0.8


def run_gaze_calibration(win, oi):
    """
    Run a 9-point gaze calibration on *win* using OpenIrisClient *oi*.
    Returns a fitted CalibrationModel, or None if cancelled/failed.
    Escape key cancels at any point.
    """
    mon  = win.monitor
    w_cm = mon.getWidth()
    dist = mon.getDistance()
    px_w, px_h = mon.getSizePix()
    h_cm = w_cm * px_h / px_w
    hw   = math.degrees(math.atan(w_cm / 2 / dist))
    hh   = math.degrees(math.atan(h_cm / 2 / dist))

    # Target centres in deg (PsychoPy: y+ = up)
    targets = [(hw * (2*fx - 1), -hh * (2*fy - 1))
               for fx, fy in _CAL_FRACS]

    ring = visual.Circle(win, radius=0.6, fillColor=None,
                          lineColor="white", lineWidth=2, units="deg")
    dot  = visual.Circle(win, radius=0.18, fillColor="white",
                          lineColor=None, units="deg")

    grid_lines = []
    for fx in (0.15, 0.50, 0.85):
        x = hw * (2*fx - 1)
        grid_lines.append(visual.Line(win, start=(x, -hh), end=(x, hh),
            lineColor=[-0.5, -0.5, -0.5], lineWidth=1, units="deg"))
    for fy in (0.15, 0.50, 0.85):
        y = -hh * (2*fy - 1)
        grid_lines.append(visual.Line(win, start=(-hw, y), end=(hw, y),
            lineColor=[-0.5, -0.5, -0.5], lineWidth=1, units="deg"))

    progress = visual.TextStim(win, text="", pos=(0, -hh + 0.7),
        color=[0.5, 0.5, 0.5], height=0.45, font="Courier New", units="deg")
    msg_txt = visual.TextStim(win, text="", pos=(0, 0),
        color="white", height=0.8, font="Courier New",
        units="deg", wrapWidth=40, alignText="center")

    # Intro screen
    win.color = 0.0
    msg_txt.text = ("GAZE CALIBRATION\n\n"
                    "Fixate each white dot.\n\n"
                    "Press Escape to cancel.")
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

        settle_end  = core.getTime() + _CAL_SETTLE_S
        collect_end = settle_end + _CAL_COLLECT_S
        lx_s, ly_s, rx_s, ry_s = [], [], [], []

        while core.getTime() < collect_end:
            if event.getKeys(["escape"]):
                return None

            win.color = 0.0
            for gl in grid_lines:
                gl.draw()
            ring.pos = (tx, ty)
            dot.pos  = (tx, ty)
            ring.draw()
            dot.draw()
            progress.text = f"Point {idx + 1} / {n_pts}"
            progress.draw()
            win.flip()

            # Collect samples only during the collection window
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
            msg_txt.text = ("No gaze data received.\n"
                            "Check OpenIris connection.")
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

    # Fit model
    model = CalibrationModel()
    ok    = model.fit(cal_points)

    win.color = 0.0
    if ok:
        msg_txt.text = (f"Calibration complete!\n"
                        f"{model.n_points} points\n"
                        f"RMSE  L: {model.rmse_left:.2f}\u00b0   "
                        f"R: {model.rmse_right:.2f}\u00b0")
    else:
        msg_txt.text = "Calibration failed.\nInsufficient or collinear data."
        model = None

    msg_txt.draw()
    win.flip()
    core.wait(2.5)
    return model


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENT RUNNER
# ─────────────────────────────────────────────────────────────────────────────

class ExperimentRunner:
    """
    Runs trial sequences using PsychoPy's flip loop for frame-accurate timing.

    Timing model:
      • core.Clock reset at the start of each stimulus phase
      • win.flip() drives the render loop; each flip is synchronised to vblank
      • event.getKeys() checked every flip for response / escape
      • OpenIris events stamped before and after the first stimulus flip
        (BeforeStimON → flip → AfterStimON), mirroring VOG.m / OpenIrisSync
    """

    def __init__(self, win, stim, oi, cfg):
        self.win        = win
        self.stim       = stim
        self.oi         = oi
        self.cfg        = cfg
        self.trial_data = []
        self._aborted   = False

    def _stamp(self, msg):
        if self.oi and self.oi.connected and self.cfg.get("log_events"):
            self.oi.record_event(msg)

    def run_trial(self, i, trial, flip_sync, draw_sync):
        win   = self.win
        stim  = self.stim
        ttype = trial["type"]
        n     = i + 1

        fix_dur  = trial["fix_dur_ms"]  / 1000.0
        gap_dur  = trial.get("gap_dur_ms", 0) / 1000.0
        stim_dur = trial.get("stim_dur_ms", 0) / 1000.0

        resp_key = ""
        rt_ms    = ""
        clock    = core.Clock()

        event.clearEvents()

        # ── Phase 1: Fixation ──────────────────────────────────────────────
        self._stamp(f"FIXATION_ON trial={n:03d} type={ttype.upper()}")
        clock.reset()
        flip_sync()
        draw_sync()
        win.flip()
        while clock.getTime() < fix_dur:
            win.color = 0.0
            stim.draw_fixation()
            stim.draw_status()
            draw_sync()
            win.flip()
            keys = event.getKeys(["escape", "space"])
            if "escape" in keys:
                self._aborted = True
                return None
            if "space" in keys and not resp_key:
                resp_key = "space"
                rt_ms    = round(clock.getTime() * 1000, 2)

        # ── Phase 2: Gap ───────────────────────────────────────────────────
        if gap_dur > 0:
            self._stamp(f"GAP_ON trial={n:03d}")
            clock.reset()
            flip_sync()
            draw_sync()
            win.flip()
            while clock.getTime() < gap_dur:
                win.color = 0.0
                stim.draw_status()
                draw_sync()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        # ── Phase 3: Stimulus ──────────────────────────────────────────────
        self._stamp(f"BeforeStimON trial={n:03d} type={ttype.upper()}")
        actual_onset = 0.0

        if ttype == "fixation":
            clock.reset()
            win.color = 0.0
            stim.draw_fixation()
            stim.draw_status()
            flip_sync()
            draw_sync()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_fixation()
                stim.draw_status()
                draw_sync()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "saccade":
            side = trial["side"]
            ecc  = trial["eccentricity"]
            tx   = -ecc if side == "left" else ecc
            self._stamp(f"BeforeStimON trial={n:03d} "
                        f"SACCADE side={side} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_dot(tx, 0)
            stim.draw_status()
            flip_sync()
            draw_sync()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_dot(tx, 0)
                stim.draw_status()
                draw_sync()
                win.flip()
                keys = event.getKeys(["escape", "space"])
                if "escape" in keys:
                    self._aborted = True
                    return None
                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms    = round((clock.getTime() - actual_onset) * 1000, 2)

        elif ttype == "eccentric_fixation":
            side = trial["side"]
            ecc  = trial["eccentricity"]
            tx   = -ecc if side == "left" else ecc
            self._stamp(f"BeforeStimON trial={n:03d} "
                        f"ECC_FIX side={side} ecc={ecc}deg")
            clock.reset()
            win.color = 0.0
            stim.draw_fixation(tx, 0)
            stim.draw_status()
            flip_sync()
            draw_sync()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()
            while clock.getTime() < stim_dur:
                win.color = 0.0
                stim.draw_fixation(tx, 0)
                stim.draw_status()
                draw_sync()
                win.flip()
                if "escape" in event.getKeys(["escape"]):
                    self._aborted = True
                    return None

        elif ttype == "pursuit":
            amp   = trial["amplitude"]
            speed = trial["speed"]
            direc = trial["direction"]
            self._stamp(f"BeforeStimON trial={n:03d} "
                        f"PURSUIT dir={direc} spd={speed}dps")

            if direc == "left-to-right":
                start_x, end_x = -amp, amp
            elif direc == "right-to-left":
                start_x, end_x = amp, -amp
            else:
                start_x, end_x = -amp, amp  # oscillate handled below

            if direc == "oscillate":
                freq    = speed / (2 * amp) if amp > 0 else 0.5
                t_end   = stim_dur
            else:
                sweep_s = abs(end_x - start_x) / speed if speed > 0 else stim_dur
                t_end   = min(stim_dur, sweep_s)

            clock.reset()
            win.color = 0.0
            stim.draw_pursuit_guide(amp)
            stim.draw_dot(start_x if direc != "oscillate" else 0, 0)
            stim.draw_status()
            flip_sync()
            draw_sync()
            win.flip()
            self._stamp(f"AfterStimON trial={n:03d}")
            actual_onset = clock.getTime()

            while clock.getTime() < t_end:
                t = clock.getTime()
                if direc == "oscillate":
                    x = amp * math.sin(2 * math.pi * freq * t)
                else:
                    prog = min(t / (t_end if t_end > 0 else 1), 1.0)
                    x = start_x + (end_x - start_x) * prog
                win.color = 0.0
                stim.draw_pursuit_guide(amp)
                stim.draw_dot(x, 0)
                stim.draw_status()
                flip_sync()
                draw_sync()
                win.flip()
                keys = event.getKeys(["escape", "space"])
                if "escape" in keys:
                    self._aborted = True
                    return None
                if "space" in keys and not resp_key:
                    resp_key = "space"
                    rt_ms    = round((clock.getTime() - actual_onset) * 1000, 2)

        else:
            return None

        actual_dur_ms = round(clock.getTime() * 1000, 2)
        self._stamp(f"STIM_OFF trial={n:03d}")

        return {
            "trial_num":        n,
            "type":             ttype,
            "side":             trial.get("side", ""),
            "eccentricity_deg": trial.get("eccentricity", ""),
            "amplitude_deg":    trial.get("amplitude", ""),
            "speed_deg_s":      trial.get("speed", ""),
            "direction":        trial.get("direction", ""),
            "fix_dur_ms":       trial["fix_dur_ms"],
            "gap_dur_ms":       trial.get("gap_dur_ms", 0),
            "stim_dur_ms":      trial.get("stim_dur_ms", 0),
            "actual_dur_ms":    actual_dur_ms,
            "response_key":     resp_key,
            "rt_ms":            rt_ms,
            "timestamp":        datetime.now().isoformat(),
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


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION DIALOGS
# ─────────────────────────────────────────────────────────────────────────────

def _dlg_screen():
    """Screen / monitor / OpenIris / output settings."""
    d = gui.Dlg(title="OculoStim — Setup")
    d.addText("── SCREEN ──────────────────────────────────")
    d.addField("Viewing distance (cm):",        57.0)
    d.addField("Screen width (cm):",            52.7)
    d.addField("Resolution (px) — width:",      1920)
    d.addField("Resolution (px) — height:",     1080)
    d.addField("Screen number (0 = primary):",  0)
    d.addText("")
    d.addText("── PARADIGM ─────────────────────────────────")
    d.addField("Mode:", choices=["Saccade Block", "Pursuit Block",
                                  "Fixation Block", "Mixed Block"])
    d.addText("")
    d.addText("── OPENIRIS ─────────────────────────────────")
    d.addField("Host:",                         "127.0.0.1")
    d.addField("Port:",                         9003)
    d.addField("Connect to OpenIris?",          True)
    d.addField("Auto-record with experiment?",  True)
    d.addField("Log trial events?",             True)
    d.addField("Calibrate gaze?",               False)
    d.addField("Photodiode sync square?",       False)
    d.addText("")
    d.addText("── OUTPUT ───────────────────────────────────")
    d.addField("Session name:",                 "oculostim")
    d.addField("Output folder:",                str(Path.home()))
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "screen_dist":   float(v[0]),
        "screen_w_cm":   float(v[1]),
        "screen_w_px":   int(v[2]),
        "screen_h_px":   int(v[3]),
        "screen_num":    int(v[4]),
        "mode":          v[5],
        "oi_host":       v[6],
        "oi_port":       int(v[7]),
        "oi_connect":    bool(v[8]),
        "auto_record":   bool(v[9]),
        "log_events":    bool(v[10]),
        "do_calibrate":  bool(v[11]),
        "sync_sq":       bool(v[12]),
        "session":       str(v[13]),
        "output_folder": str(v[14]),
    }


def _dlg_saccade():
    d = gui.Dlg(title="Saccade Block")
    d.addField("Eccentricity — deg, comma-separated:", "10.0")
    d.addField("# Trials:",                    20)
    d.addField("Fixation duration (ms):",      1000)
    d.addField("Fix. jitter ± (ms):",          0)
    d.addField("Gap duration (ms):",           0)
    d.addField("Target duration (ms):",        1000)
    d.addField("Balance:", choices=["interleaved", "random",
                                     "left only", "right only"])
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials":       int(v[1]),
        "fix_dur_ms":     int(v[2]),
        "fix_jitter_ms":  int(v[3]),
        "gap_dur_ms":     int(v[4]),
        "stim_dur_ms":    int(v[5]),
        "balance":        v[6],
    }


def _dlg_pursuit():
    d = gui.Dlg(title="Pursuit Block")
    d.addField("Amplitude ± (deg):",           12.0)
    d.addField("Speed (deg/s):",               10.0)
    d.addField("# Trials:",                    10)
    d.addField("Fixation duration (ms):",      1000)
    d.addField("Fix. jitter ± (ms):",          0)
    d.addField("Sweep duration (ms):",         3000)
    d.addField("Direction:", choices=["alternating", "left-to-right",
                                       "right-to-left", "oscillate"])
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "amplitude":     float(v[0]),
        "speed":         float(v[1]),
        "n_trials":      int(v[2]),
        "fix_dur_ms":    int(v[3]),
        "fix_jitter_ms": int(v[4]),
        "stim_dur_ms":   int(v[5]),
        "direction":     v[6],
    }


def _dlg_fixation():
    d = gui.Dlg(title="Fixation Block")
    d.addField("Eccentricities — deg, comma-separated:", "5, 10, 15")
    d.addField("# Trials:",                    20)
    d.addField("Central fixation duration (ms):", 1000)
    d.addField("Fix. jitter ± (ms):",          0)
    d.addField("Eccentric fixation duration (ms):", 1000)
    d.addField("Sides:", choices=["both", "left only", "right only"])
    d.addField("Order:", choices=["random", "sequential"])
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {
        "eccentricities": _parse_eccentricities(v[0]),
        "n_trials":       int(v[1]),
        "fix_dur_ms":     int(v[2]),
        "fix_jitter_ms":  int(v[3]),
        "stim_dur_ms":    int(v[4]),
        "sides":          v[5],
        "order":          v[6],
    }


def _dlg_mixed():
    d = gui.Dlg(title="Mixed Block — Fixation-only Trials")
    d.addText("Saccade and Pursuit parameters were set in the previous dialogs.")
    d.addField("# Fixation-only trials:",      5)
    d.addField("Fixation-only duration (ms):", 2000)
    d.show()
    if not d.OK:
        return None
    v = d.data
    return {"fix_n": int(v[0]), "fix_dur_ms": int(v[1])}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Screen / mode / OpenIris config ───────────────────────────────────
    cfg = _dlg_screen()
    if cfg is None:
        return

    if not cfg["output_folder"].strip():
        picked = choose_folder()
        if not picked:
            return
        cfg["output_folder"] = picked

    mode = cfg["mode"]

    # ── 2. Paradigm parameters ────────────────────────────────────────────────
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

    # ── 3. Build trials ───────────────────────────────────────────────────────
    if mode == "Saccade Block":
        trials = build_saccade_trials(s_cfg)
    elif mode == "Pursuit Block":
        trials = build_pursuit_trials(p_cfg)
    elif mode == "Fixation Block":
        trials = build_fixation_block_trials(f_cfg)
    else:
        trials = build_mixed_trials(s_cfg, p_cfg,
                                    m_cfg["fix_n"], m_cfg["fix_dur_ms"])

    if not trials:
        d = gui.Dlg(title="OculoStim")
        d.addText("No trials were generated. Check your parameters.")
        d.show()
        return

    # ── 4. OpenIris connection ────────────────────────────────────────────────
    oi = OpenIrisClient(cfg["oi_host"], cfg["oi_port"])

    print("Trying to connect to OpenIris...")
    
    if cfg["oi_connect"]:
        ok = oi.connect()

        print("Connected:", ok)
        
        if not ok:
            d = gui.Dlg(title="OpenIris — Connection Failed")
            d.addText(f"Could not reach OpenIris at "
                      f"{cfg['oi_host']}:{cfg['oi_port']}.")
            d.addText("Continuing without OpenIris.")
            d.show()

    # ── 5. PsychoPy window ────────────────────────────────────────────────────
    mon = monitors.Monitor("oculostim",
                           width=cfg["screen_w_cm"],
                           distance=cfg["screen_dist"])
    mon.setSizePix((cfg["screen_w_px"], cfg["screen_h_px"]))

    win = visual.Window(
        size=(cfg["screen_w_px"], cfg["screen_h_px"]),
        monitor=mon,
        units="deg",
        fullscr=True,
        screen=cfg["screen_num"],
        color=0.0,
        colorSpace="rgb",
        allowGUI=False,
        waitBlanking=True,
    )
    win.mouseVisible = False

    stim = StimulusPresenter(win)
    stim.sync_enabled = cfg["sync_sq"]

    # ── 6. Session name → OpenIris ────────────────────────────────────────────
    # if oi.connected:
    #    oi._send(f"CHANGESETTING|SessionName|{cfg['session']}")

    # ── 7. Gaze calibration ───────────────────────────────────────────────────
    cal_model = None
    if oi.connected and cfg["do_calibrate"]:
        cal_model = run_gaze_calibration(win, oi)

        # Save gaze calibration model
        if cal_model and cal_model.valid:
            try:
                from pathlib import Path
                import json
                from datetime import datetime

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cal_path = Path(cfg["output_folder"]) / f"oculostim_{cfg['session']}_calibration_{ts}.json"

                cal_data = {
                    "session": cfg["session"],
                    "timestamp": ts,
                    "n_points": cal_model.n_points,
                    "rmse_left": cal_model.rmse_left,
                    "rmse_right": cal_model.rmse_right,
                    "left_eye": {
                        "x_coeffs": cal_model._lx,
                        "y_coeffs": cal_model._ly,
                    },
                    "right_eye": {
                        "x_coeffs": cal_model._rx,
                        "y_coeffs": cal_model._ry,
                    }
                }

                with open(cal_path, "w") as f:
                    json.dump(cal_data, f, indent=2)

                print(f"[Calibration saved] {cal_path}")

            except Exception as e:
                print(f"[Calibration save failed] {e}")

    # ── 8. Run experiment ─────────────────────────────────────────────────────
    cfg["mode"] = mode
    runner = ExperimentRunner(win, stim, oi, cfg)

    stim.show_message(f"OculoStim\n\n"
                      f"{mode}  —  {len(trials)} trials\n\n"
                      f"Press any key to begin.\nEscape aborts at any time.")
    event.waitKeys()

    runner.run(trials)

  

    # ── 10. Cleanup ───────────────────────────────────────────────────────────
    win.close()
    oi.disconnect()

    d = gui.Dlg(title="OculoStim — Complete")
    d.addText(f"Block complete: {n_done} / {len(trials)} trials")
    if saved_msg:
        d.addText(saved_msg)
    d.show()


if __name__ == "__main__":
    main()
