import os
import wx
import threading
import mss 
import numpy as np

class ExperimenterMonitor(wx.Frame):
    def __init__(self, parent):
        super(ExperimenterMonitor, self).__init__(parent, title="See What They See", size=(800, 600))
        self.panel = ExperimenterMonitorPanel(self)
        self.Show()

class ExperimenterMonitorPanel(wx.Panel):
    def __init__(self, parent):
        super(ExperimenterMonitorPanel, self).__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.bitmap = None
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_refresh, self.timer)
        self.timer.Start(100)

    def see_what_they_see(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1] # PSYCHOPY
            shot = sct.grab(monitor)
            img = np.array(shot)
            rgb = img[:, :, :3][:, :, ::-1]
            h, w = rgb.shape[:2]
            wx_image = wx.Image(w, h)
            wx_image.SetData(rgb.tobytes())
            self.bitmap = wx.Bitmap(wx_image)
        self.Refresh()

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()
        if not self.bitmap:
            return
        panel_w, panel_h = self.GetClientSize()
        image = self.bitmap.ConvertToImage()
        image = image.Scale(panel_w, panel_h, wx.IMAGE_QUALITY_HIGH)
        scaled_bmp = wx.Bitmap(image)
        dc.DrawBitmap(scaled_bmp, 0, 0)
    
    def on_refresh(self, event):
        self.see_what_they_see()