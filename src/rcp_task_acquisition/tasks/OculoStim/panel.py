# -*- coding: utf-8 -*-
import os
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/OculoStimPanel") 

class OculoStimPanel(TrialPanel):
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
        self.selection = ""
        self.image_list = []

        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))

        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_oculostim_controls(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)

    def _setup_oculostim_controls(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        
        self.hand_text = wx.StaticText(self, label='Choose which paradigm to run:')
        self.saccade_radio = wx.RadioButton(self, label="Saccade", style= wx.RB_GROUP)
        self.pursuit_radio = wx.RadioButton(self, label="Smooth Pursuit")
        self.fixation_radio = wx.RadioButton(self, label="Fixation")
        
        self.seconds_text = wx.StaticText(self, label= "Time: 0 secs")
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
    
        grid_sizer = wx.GridBagSizer(6, 6)
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.saccade_radio, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.pursuit_radio, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.fixation_radio, pos=(2, 4), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(3, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(4, 0), span=(0,3), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer

    def run_trial(self, number):
        self.seconds = 0
        self.saccade_radio.Enable(False)
        self.pursuit_radio.Enable(False)
        self.fixation_radio.Enable(False)
        self.trial_text.SetLabel(f"Trial # {number}")
        self.trial_is_active = True
    
    def update_trial(self, number):
        self.trial_number = number
        
    def get_result(self):
        if self.fixation_radio.GetValue():
            self.selection = "Fixation"
        elif self.saccade_radio.GetValue():
            self.selection = "Saccade"
        elif self.pursuit_radio.GetValue():
            self.selection = "Pursuit"
        print(f"OculoStim,{self.selection},{self.trial_number}")
        return f"OculoStim,{self.selection},{self.trial_number}"

    def reset(self, number):
        self.seconds = 5
        self.saccade_radio.Enable(True)
        self.pursuit_radio.Enable(True)
        self.fixation_radio.Enable(True)
        self.seconds_text.SetLabel(f"Time: 0 secs")
        self.continue_button.SetValue(False)
        self.continue_button.SetLabel("Begin Trial")
        self.trial_text.SetLabel(f"Trial # {number+1}")
    
    def on_timer(self, event):
        self.seconds+=1
        self.display_mins = int(self.seconds/60)
        self.display_secs = self.seconds%60
        if self.trial_is_active:
            self.seconds_text.SetLabel(f"Time: {self.display_mins} mins, {self.display_secs} secs")


