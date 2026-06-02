# -*- coding: utf-8 -*-
import os
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/IndefiniteRecordingPanel") 

class IndefiniteRecordingPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seconds = 0
        self.display_secs = 0
        self.display_mins = 0
        self.trial_number = 1
        self.timestamps ={}
        self.countdown_start = 0
        self.image_path = []
        self.button_width = 76
        self.border = 5
        self.photo = None
        self.selection = 0
        self.image_list = []
        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))

        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        self.seconds_text = wx.StaticText(self, label= "Time: 0 mins, 0 secs")
        vertical_sizer.Add(self.seconds_text)
        self._setup_blank_controls()
        self.SetSizer(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)

    def run_trial(self, number):
        print("run trial start")
        self.seconds = 0
        self.trial_number = number
        self.trial_is_active = True

    def update_trial(self, number):
        self.trial_number = number
        
    def get_result(self):
        return f"IndefiniteRecording,{self.trial_number}"

    def reset(self, number):
        self.seconds = 0
        self.trial_number = number
        self.trial_is_active = False
        self.seconds_text.SetLabel("Time: 0 mins, 0 secs")
    
    def on_timer(self, event):
        self.seconds+=1
        self.display_mins = int(self.seconds/60)
        self.display_secs = self.seconds%60
        if self.trial_is_active:
            self.seconds_text.SetLabel(f"Time: {self.display_mins} mins, {self.display_secs} secs")


