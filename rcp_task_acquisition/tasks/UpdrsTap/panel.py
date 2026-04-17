# -*- coding: utf-8 -*-
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.UpdrsTap.constants import BASIC_TAPS_PATH
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panel/UpdrsTap")


class FingerTapPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tap_hand = "left"
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_fingertap(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        vertical_sizer.Add(self.setup_instruction_playback(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.instruction_paths = BASIC_TAPS_PATH
        self.start_video_button.Enable(True)
        self.SetSizer(vertical_sizer)
        
    def _setup_fingertap(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        
        self.hand_text = wx.StaticText(self, label='Choose which hand trial will use:')
        self.left_radio = wx.RadioButton(self, label="Left Hand", style= wx.RB_GROUP)
        
        self.left_radio.Bind(wx.EVT_RADIOBUTTON, self.on_select)
        self.right_radio = wx.RadioButton(self, label="Right Hand")
        self.right_radio.Bind(wx.EVT_RADIOBUTTON, self.on_select)
        
        self.seconds_text = wx.StaticText(self, label= "Time: 10 secs")
        
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
    
        grid_sizer = wx.GridBagSizer(5, 4)
        
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.left_radio, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.right_radio, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(3, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(4, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer
    
    def run_trial(self, number):
        self.seconds = 10
        self.left_radio.Enable(False)
        self.right_radio.Enable(False)
        self.hand_text.Enable(False)
        self.start_video_button.Enable(False)
        # self.trial_text.SetLabel(f"Trial # {number}")
    
        
    def get_result(self):
        self.tap_hand = "left" if self.left_radio.GetValue() else "right"
        return self.tap_hand
        
    
    def on_select(self, event):
        self.tap_hand = "left" if self.left_radio.GetValue() else "right"

    
    def reset(self, trial):
        self.seconds = 10
        self.left_radio.Enable(True)
        self.right_radio.Enable(True)
        self.hand_text.Enable(True)
        self.seconds_text.SetLabel(f"Time: {self.seconds} secs")
        # self.continue_button.Enable(False)
        self.continue_button.SetValue(False)
        self.continue_button.SetLabel("Begin Trial")
        self.trial_text.SetLabel(f"Trial # {trial+1}")
        self.start_video_button.Enable(True)
    
    def start_new_trial(self):
        self.trial_number = 0
        self.trial_text.SetLabel("Trial # 1")
        
    def on_timer(self, event):
        self.seconds-=1
        if self.seconds >= 0:
            self.seconds_text.SetLabel(f"Time: {self.seconds} secs")
        # else:
        #     self.continue_button.Enable(True)