# -*- coding: utf-8 -*-
import wx
from datetime import datetime

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.NBack.configs import NBACK_TYPES
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/NBack")


class NbackPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trial_type= "real"
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_nback(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        
        
    def _setup_nback(self):
        self.choice_list = ["1-back", "2-back"]
        
        self.practice = wx.RadioButton(self, label="Practice Trial", style= wx.RB_GROUP)
        self.real = wx.RadioButton(self, label="Real Trial")
        
        trial = wx.StaticText(self, label='Select N-back')
        self.nback_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=NBACK_TYPES,
                                       size=(200, -1))
        self.nback_choice.SetSelection(0)
        
        text = wx.StaticText(self, label='Select trial type')
        self.continue_button = wx.ToggleButton(self, label="Start Trial")
    
        grid_sizer = wx.GridBagSizer(5, 4)

        grid_sizer.Add(trial, pos=(0, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        grid_sizer.Add(self.nback_choice, pos=(0, 2), span=(0,2), flag=wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, border=10)
        
        grid_sizer.Add(text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        grid_sizer.Add(self.practice, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT| wx.TOP | wx.BOTTOM, border=10)
        grid_sizer.Add(self.real, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, border=10)
        grid_sizer.Add(self.continue_button, pos=(4, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.TOP, border=10)
        return grid_sizer
    
    
    def continue_event(self, event):
        self.rest_timer.Stop()
        self.selections = {"type": NBACK_TYPES[self.nback_choice.GetSelection()],
                           "trial": self.trial_type}
        self.timestamps[f'{datetime.utcnow().strftime("%Y%m%d%H%M%S")}Z'] = "next_trial_selected"
    
    def update_trial(self, number):
        self.trial_text.SetLabel(f"Selection for Trial # {number}")
        
    def get_result(self):
        self.trial_type = "practice" if self.practice.GetValue() else "real"
        return f"{self.trial_type},{NBACK_TYPES[self.nback_choice.GetSelection()]}"
        
    def run_trial(self, number):
        self.nback_choice.Enable(False)
        self.practice.Enable(False)
        
        

    def cancel_event(self, event):
        self.cancel = True
        self.rest_timer.Stop()
        
        
    def reset(self, number):
        self.nback_choice.Enable(True)
        self.practice.Enable(True)
        self.continue_button.Enable(True)
        self.continue_button.Enable(True)
        self.continue_button.SetValue(False)
        self.continue_button.SetLabel("Start Trial")
    

    def on_timer(self, event):
        self.seconds+=1