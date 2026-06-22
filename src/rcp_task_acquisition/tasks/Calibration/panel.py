# -*- coding: utf-8 -*-
import os
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
import rcp_task_acquisition.tasks.NaturalisticSpeech.constants as c
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/NaturalisticSpeechPanel") 



class Calibration(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seconds = 0
        self.display_secs = 0
        self.display_mins = 0
        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._set_up_timer(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)
     

    def _set_up_timer(self):
        self.seconds_text = wx.StaticText(self, label= "Time: 0 mins, 0 secs")
        grid_sizer = wx.GridBagSizer(5, 4)
        grid_sizer.Add(self.seconds_text, pos=(4, 0), span=(0, 4), flag=wx.ALIGN_LEFT |  wx.ALL, border=10)
        return grid_sizer



    
    def reset(self, number):
        self.seconds = 0
        self.seconds_text.SetLabel("Time: 0 mins, 0 secs")
    

    def on_timer(self, event):
        self.seconds+=1
        self.display_mins = int(self.seconds/60)
        self.display_secs = self.seconds%60
        self.seconds_text.SetLabel(f"Time: {self.display_mins} mins, {self.display_secs} secs")

