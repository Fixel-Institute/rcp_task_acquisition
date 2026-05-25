import wx
import numpy as np 
import time
from collections import deque

class DelsysPreview(wx.Frame):
    def __init__(self, parent, title):
        super(DelsysPreview, self).__init__(parent, title=title, size=(800, 500))
        splitter = wx.SplitterWindow(self)

        self.preview_panel = DelsysPreviewPanel(splitter, title)
        self.control_panel = DelsysControlPanel(splitter, onSensorChange=self.preview_panel.on_sensor_change, onIMUChange=self.preview_panel.on_imu_change)
        splitter.SplitHorizontally(self.control_panel, self.preview_panel, sashPosition=100)

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, event):
        self.preview_panel._timer.Stop()
        event.Skip()

class DelsysControlPanel(wx.Panel):
    def __init__(self, parent, onSensorChange=None, onIMUChange=None):
        super(DelsysControlPanel, self).__init__(parent)

        self.onSensorChange = onSensorChange
        self.onIMUChange = onIMUChange

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        hgroup = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self, label="Delsys Sensor #:"), 0, wx.ALL, 4)
        self.sensor_id = ["Delsys Sensor #1", "Delsys Sensor #2", "Delsys Sensor #3"]
        self.sensor_choice = wx.Choice(self, choices=self.sensor_id)
        self.sensor_choice.SetSelection(0)
        self.sensor_choice.Bind(wx.EVT_CHOICE, self.on_sensor_change)
        left.Add(self.sensor_choice, 1, wx.EXPAND | wx.ALL, 4)
        hgroup.Add(left, 4, wx.EXPAND)

        middle = wx.BoxSizer(wx.VERTICAL)
        middle.Add(wx.StaticText(self, label="IMU Sensor Choice:"), 0, wx.ALL, 4)
        self.imu_choice = wx.RadioBox(self, choices=["Accelerometer", "Gyroscope"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.imu_choice.Bind(wx.EVT_RADIOBOX, self.on_mode_change)
        middle.Add(self.imu_choice, 1, wx.EXPAND | wx.ALL, 4)
        hgroup.Add(middle, 3, wx.EXPAND)

        hgroup.AddStretchSpacer(3)

        self.sizer.Add(hgroup, 0, wx.EXPAND)
        self.SetSizer(self.sizer)

    def on_sensor_change(self, event):
        if self.onSensorChange:
            self.onSensorChange(self.sensor_choice.GetStringSelection())

    def on_mode_change(self, event):
        if self.onIMUChange:
            self.onIMUChange(self.imu_choice.GetStringSelection())

    def on_detect_change(self, event):
        self.detection_enabled = self.detect_rb1.GetValue()


class DelsysPreviewPanel(wx.Panel):
    def __init__(self, parent, title):
        super(DelsysPreviewPanel, self).__init__(parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.canvas = wx.Panel(self)
        self.sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(self.sizer)
        
        self.canvas.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.canvas.Bind(wx.EVT_PAINT, self.on_paint)
        self.canvas.Bind(wx.EVT_SIZE, self.on_resize)

        # Scale factors for EMG and imu data
        self.emg_scale = 0.05
        self.imu_scale = 16

        # cached pens for drawing
        self._pen_emg = wx.Pen("#606060", 2)
        self._pen_imu_x = wx.Pen("#F48754", 3)
        self._pen_imu_y = wx.Pen("#6985FF", 3)
        self._pen_imu_z = wx.Pen("#5FFBA3", 3)

        self.setup_signals()

        # Timer to refresh at maximum rate
        self._interval_ms = 1
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self._timer)
        self._timer.Start(self._interval_ms)

        # Measuring timer/callback rate and processing time, remove for production
        self._last_timer_ts = None
        self._intervals = deque(maxlen=120)
        self._timer_count = 0
        self.measured_fps = 0.0

    # Dummy definitions for now. We will grab the actual info from streaming sensor
    def setup_signals(self, channel=None):
        self.emg_fs = 2222.22
        self.imu_fs = 148.148
        self.window_time = 2
        emg_sizer = int(2 * self.emg_fs)
        imu_sizer = int(2 * self.imu_fs)
        self.emg_y = np.zeros(emg_sizer, dtype=float)
        self.imu_y = np.zeros((imu_sizer, 3), dtype=float)

        width, _ = self.canvas.GetClientSize()
        self.emg_x = np.arange(emg_sizer)  / emg_sizer * width
        self.emg_x = np.array(self.emg_x, dtype=int)

        self.imu_x = np.arange(imu_sizer)  / imu_sizer * width
        self.imu_x = np.array(self.imu_x, dtype=int)

    def on_sensor_change(self, sensor_name):
        print(f"Selected sensor: {sensor_name}")
        pass 

    def on_imu_change(self, sensor_name):
        print(f"Selected IMU mode: {sensor_name}")
        pass

    def get_emg_data(self):
        sample_count = int(self.emg_fs/30)
        emg_signal = np.random.normal(0, 1, sample_count) * self.emg_scale / 3
        return emg_signal
    
    def get_imu_data(self):
        sample_count = int(self.imu_fs/30)
        imu_signal = np.zeros((sample_count, 3), dtype=float)
        imu_signal[:, 0] = np.random.normal(0, 1, sample_count) 
        imu_signal[:, 1] = np.random.normal(0, 1, sample_count)
        imu_signal[:, 2] = np.random.normal(0, 1, sample_count) + 9.81
        return imu_signal
    
    def on_resize(self, event):
        self.Layout()
        self.canvas.Refresh()
        width, height = self.canvas.GetClientSize()
        emg_canvas = [width * 0.05, height * 0.35, width * 0.9, height * 0.35]
        imu_canvas = [width * 0.05, height * 0.90, width * 0.9, height * 0.50]

        self.emg_x = np.array(np.arange(len(self.emg_x), dtype=int) / len(self.emg_x) * emg_canvas[2] + emg_canvas[0], dtype=int)
        self.imu_x = np.array(np.arange(len(self.imu_x), dtype=int) / len(self.imu_x) * imu_canvas[2] + imu_canvas[0], dtype=int)
        event.Skip()

    def on_paint(self, event):
        # Setup canvas
        width, height = self.canvas.GetClientSize()
        if width <= 0 or height <= 0:
            return
        emg_canvas = [width * 0.05, height * 0.35, width * 0.9, height * 0.35]
        imu_canvas = [width * 0.05, height * 0.90, width * 0.9, height * 0.50]
        dc = wx.BufferedPaintDC(self.canvas)
        dc.SetBackground(wx.Brush(self.canvas.GetBackgroundColour()))
        dc.Clear()

        # Draw EMG signal
        dc.SetPen(self._pen_emg)
        dc.SetClippingRegion(int(emg_canvas[0]), int(emg_canvas[1]), int(emg_canvas[2]), -int(emg_canvas[3]))
        
        # Hum, step of 5 maybe too much? idk... Need testing with real data
        step = 5
        ys = np.asarray(emg_canvas[1] - (emg_canvas[3] / 2) - (self.emg_y[::step] / self.emg_scale) * (emg_canvas[3] / 2)).astype(int)
        xs = self.emg_x[::step]
        points = list(zip(xs, ys))
        if len(points) > 1:
            dc.DrawLines(points)
        dc.DestroyClippingRegion()

        # Draw IMU signal
        dc.SetClippingRegion(int(imu_canvas[0]), int(imu_canvas[1]), int(imu_canvas[2]), -int(imu_canvas[3]))
        ys = np.asarray(imu_canvas[1] - (imu_canvas[3] / 2) + (-self.imu_y / self.imu_scale) * (imu_canvas[3] / 2)).astype(int)
        xs = self.imu_x

        # IMU X axis
        dc.SetPen(self._pen_imu_x)
        pts_x = list(zip(xs, ys[:, 0]))
        if len(pts_x) > 1:
            dc.DrawLines(pts_x)

        # IMU Y axis
        dc.SetPen(self._pen_imu_y)
        pts_y = list(zip(xs, ys[:, 1]))
        if len(pts_y) > 1:
            dc.DrawLines(pts_y)

        # IMU Z axis
        dc.SetPen(self._pen_imu_z)
        pts_z = list(zip(xs, ys[:, 2]))
        if len(pts_z) > 1:
            dc.DrawLines(pts_z)

        dc.DestroyClippingRegion()

        # Draw x-axis with tick marks from -2s to 0s
        dc.SetPen(wx.Pen("#000000", 3))
        dc.SetClippingRegion(0, 0, width, height)
        dc.DrawLine(int(imu_canvas[0]), int(imu_canvas[1]), int(imu_canvas[0]+imu_canvas[2]), int(imu_canvas[1]))
        ticks = np.arange(-self.window_time, 0.0001, 0.5)
        for t in ticks:
            norm = (t + self.window_time) / self.window_time
            x = int(norm * imu_canvas[2] + imu_canvas[0])
            dc.DrawLine(x, int(imu_canvas[1]), x, int(imu_canvas[1]) + 6)
            label = f"{t:.1f}s"
            dc.DrawText(label, x - 12, int(imu_canvas[1]) + 8)

        # Draw y-axis for both EMG and IMU
        dc.DrawLine(int(imu_canvas[0]), int(imu_canvas[1]), int(imu_canvas[0]), int(imu_canvas[1] - imu_canvas[3]))
        dc.DrawLine(int(emg_canvas[0]), int(emg_canvas[1]), int(emg_canvas[0]), int(emg_canvas[1] - emg_canvas[3]))
        
        # Add labels for EMG and IMU
        dc.DrawText(f"EMG ({self.emg_scale:.1f} V)", int(emg_canvas[0]) + 5, int(emg_canvas[1]) - int(emg_canvas[3]) + 5)
        dc.DrawText(f"IMU ({self.imu_scale:.1f} g)", int(imu_canvas[0]) + 5, int(imu_canvas[1]) - int(imu_canvas[3]) + 5)

        event.Skip()

    def on_timer(self, event):
        # Measure callback interval and processing time (remove for production)
        t_start = time.perf_counter()
        if self._last_timer_ts is not None:
            interval = t_start - self._last_timer_ts
            self._intervals.append(interval)
            if len(self._intervals) >= 3:
                mean_int = sum(self._intervals) / len(self._intervals)
                self.measured_fps = 1.0 / mean_int if mean_int > 0 else 0.0
        self._last_timer_ts = t_start

        # Main processing (get data and update buffer)
        # But wait, this actually only works for normal sensor, not the analog sensor... 
        emg_data = self.get_emg_data()
        imu_data = self.get_imu_data()

        n = len(emg_data)
        if n >= self.emg_y.size:
            self.emg_y = emg_data[-self.emg_y.size:]
        else:
            self.emg_y[:-n] = self.emg_y[n:]
            self.emg_y[-n:] = emg_data

        n = len(imu_data)
        if n >= self.imu_y.size:
            self.imu_y = imu_data[-self.imu_y.size:, :]
        else:
            self.imu_y[:-n, :] = self.imu_y[n:, :]
            self.imu_y[-n:, :] = imu_data

        proc_time = time.perf_counter() - t_start
        self._timer_count += 1

        # Print stats every 200 callbacks to avoid spam (remove for production) 
        # Testing environment is about 200Hz refresh rate on a 2017 iMac without considering Delsys delays. 
        if self._timer_count % 200 == 0:
            print(f"Timer called {self._timer_count} times — mean interval { (sum(self._intervals)/len(self._intervals)) if self._intervals else 0:.4f}s -> {self.measured_fps:.1f} Hz; processing {proc_time*1000:.1f} ms")

        if self and self.canvas:
            self.canvas.Refresh(False)