# -*- coding: utf-8 -*-
import wx
import wx.lib.dialogs
import mss
import numpy as np

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/ParticipantMonitorPanel") 


def get_proportions(original_size, scaled_width):
    #basing proportions on width bc there is less wiggle room on the display
    scale_factor = scaled_width/original_size[0]
    scaled_height = int(original_size[1]*scale_factor)
    return (scaled_width, scaled_height)
        


class MonitorPanel(wx.Panel):
    def __init__(self, parent, psychopy_monitor, display_size):
        self.parent = parent
        self.psychopy_monitor = psychopy_monitor+1
        max_gui_image_size = (346, 216)
        self.display_size = get_proportions(display_size, max_gui_image_size[0])
        self.prev_arr = None


    def create_panel(self):
        title = wx.StaticText(self.parent, label= "Participant Monitor:")
        font = wx.Font(wx.FontInfo(8).Bold())
        title.SetFont(font)
        
        self.monitor_bitmap = wx.StaticBitmap(self.parent, wx.ID_ANY)
        self.monitor_bitmap.SetBitmap(wx.NullBitmap)

        image_sizer = wx.GridBagSizer(3, 4)
        image_sizer.Add(title, pos=(0, 0), span=(0, 4),flag=wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT, border=5)        
        image_sizer.Add(self.monitor_bitmap, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.LEFT, border=5)
        
        self.update_screen()
        self.parent.Layout()
        return image_sizer
        
    
    def update_screen(self):
        with mss.MSS() as sct:
            monitor = sct.monitors[self.psychopy_monitor]
            shot = sct.grab(monitor)
            img = np.array(shot)
            # only update the gui when they are different
            if self.prev_arr is not None and np.array_equal(img, self.prev_arr):
                return
            rgb = img[:, :, :3][:, :, ::-1]
            h, w = rgb.shape[:2]
            wx_image = wx.Image(w, h)
            wx_image.SetData(rgb.tobytes())
            wx_image = wx_image.Scale(self.display_size[0], self.display_size[1])
            wx_image.ConvertToBitmap()
            self.prev_arr = img
            self.monitor_bitmap.SetBitmap(wx_image) 
        self.parent.Layout()

    def update_screen_event(self, event):
        self.update_screen()

 