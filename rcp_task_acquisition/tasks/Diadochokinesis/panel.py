# -*- coding: utf-8 -*-
import wx
import numpy as np

from rcp_task_acquisition.tasks.Diadochokinesis.constants import (DDK_TRIAL_TIME, 
                                                                  DDK_TRIALS, 
                                                                  DDK_PATHS, 
                                                                  DDK_TRIALS_PER_SYLLABLE)
from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panel/Diadochokinesis")


class DdkPanel(TrialPanel):
    def __init__(self, parent=None):
        self.param_list = np.repeat(np.array(DDK_TRIALS), DDK_TRIALS_PER_SYLLABLE).tolist()
        self.trial_number_ = 1
        self.trials = {}
        self.syllable_count = 0
        self.syllable = str(self.param_list[0])
        self.trials["trial_0"] = str(self.syllable)
        self.video_buttons = []
        self.other_buttons = []
        super().__init__(parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        static_box_sizer = self.setup_instruction_playback()
        vertical_sizer.Add(self._setup_ddk(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        vertical_sizer.Add(self.add_video_panel(static_box_sizer), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizerAndFit(vertical_sizer)
        
        self.instruction_paths = DDK_PATHS #["introduction"]
        self.video_title.SetLabel("Instructions Overview: ")
        self.start_video_button.Enable(True)
        
        
    def _setup_ddk(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        self.syllable_text = wx.StaticText(self, label=f"Syllable: {self.syllable}")
        self.seconds_text = wx.StaticText(self, label= f"Time: {DDK_TRIAL_TIME} secs")

        self.continue_button = wx.ToggleButton(self, label="Begin Trial")
        self.next_button = wx.Button(self, label="Next Trial")
        self.next_button.Bind(wx.EVT_BUTTON, self.next_trial)
    
        grid_sizer = wx.GridBagSizer(5, 6)
        
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.syllable_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(2, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(3,0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.next_button, pos=(3,2), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)  
        return grid_sizer


    def add_video_panel(self, static_box_sizer):
        self.syllable_video_title = wx.StaticText(self, label=f"Syllable ({self.syllable}) Instructions:")
        self.syllable_start_video_button = wx.ToggleButton(self, label="Play Video", size=(self.button_width*2, -1))
        self.syllable_pause_video_button = wx.ToggleButton(self, label="Pause Video", size=(self.button_width*2, -1))
        self.syllable_pause_video_button.Enable(False)
        
        grid_sizer = wx.GridBagSizer(3,2)
        grid_sizer.Add(self.syllable_video_title, pos=(0, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.syllable_start_video_button, pos=(1, 0), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.syllable_pause_video_button, pos=(1, 1), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)

        static_box_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, self.border)
        return static_box_sizer
        
    
    def next_trial(self, event):
        if self.trial_number_ < len(self.param_list):
            self.syllable = self.param_list[self.trial_number_]
            self.syllable_text.SetLabel(f"Syllable: {self.syllable}")
            self.continue_button.SetLabel("Begin Trial")
            self.trials[f"trial_{self.trial_number_}"] = str(self.syllable)
            self.trial_number_+=1
            self.trial_text.SetLabel(f"Trial # {self.trial_number_}")
            self.syllable_video_title.SetLabel(f"Syllable ({self.syllable}) Instructions:")
        else:
            self.syllable_text.SetLabel("Task Finished! Press 'End Task' to save data.")
            self.seconds_text.SetLabel("")
            self.trial_text.SetLabel("")
            self.continue_button.Enable(False)
            self.next_button.Enable(False)
    
    
    def reset(self, number):
        self.seconds = 0
        self.seconds_text.SetLabel(f"Time: {DDK_TRIAL_TIME} secs")
        self.syllable_text.SetLabel(f"Syllable: {self.syllable}")
        self.next_button.Enable(True)
        self.continue_button.SetLabel("Repeat Trial")
        self.continue_button.SetValue(False)
        

    def get_result(self): 
        return self.syllable
    
    
    def get_instruction(self, count):
        if self.syllable_start_video_button.GetValue():
            key_end = "_1" if self.trial_number_%3 == 1 else ""
            value = f"{self.syllable}{key_end}"
        else:
            value = "introduction"
        return value
    
    
    def run_trial(self, count):
        self.seconds = DDK_TRIAL_TIME
        self.trial_is_active = True
        self.continue_button.SetLabel("Stop Trial")
        self.next_button.Enable(False)
        self.start_video_button.Enable(False)
        self.syllable_start_video_button.Enable(False)
      
        
    def on_timer(self, event):
        if self.trial_is_active:
            self.seconds-=1
            if self.seconds >= 0:
                self.seconds_text.SetLabel(f"Time: {self.seconds} secs")


    def get_buttons(self):
        if self.syllable_start_video_button.GetValue():
            self.video_buttons = [self.syllable_start_video_button, self.syllable_pause_video_button]
            self.other_buttons = [self.start_video_button, self.pause_video_button]
        elif self.start_video_button.GetValue():
            self.video_buttons = [self.start_video_button, self.pause_video_button]
            self.other_buttons = [self.syllable_start_video_button, self.syllable_pause_video_button]

                                  
    def end_trial(self):
        super().end_trial()
        self.syllable_start_video_button.Enable(True)
        
        
    def start_video(self):
        self.get_buttons()
        self.next_button.Enable(False)
        self.continue_button.Enable(False)
        self.video_buttons[0].SetLabel("Stop Video")
        self.video_buttons[0].Enable(True)
        self.video_buttons[1].Enable(True)
        
        self.other_buttons[0].Enable(False)
        self.other_buttons[1].Enable(False)
    
    
    def stop_video(self):
        self.video_buttons[0].SetLabel("Start Video")
        self.video_buttons[0].SetValue(False)
        if self.video_buttons[1].GetValue():
            self.video_buttons[1].SetValue(False)
            self.video_buttons[1].SetLabel("Pause Video")
        
        self.video_buttons[1].Enable(False)
        self.other_buttons[0].Enable(True)
        
        self.next_button.Enable(True)
        self.continue_button.Enable(True)
    
    
    def pause_video(self):
        self.video_buttons[1].SetLabel("Resume Video")
    
    
    def resume_video(self):
        self.video_buttons[1].SetLabel("Pause Video")
        
        
    def start_new_trial(self):
        self.trial_number_ = 1
        self.trials = {}
        self.syllable_count = 0
        self.syllable = str(self.param_list[0])
        self.trials["trial_0"] = str(self.syllable)
        self.video_buttons = []
        self.other_buttons = []
        self.next_button.Enable(True)
        self.continue_button.Enable(True)
        self.seconds_text.SetLabel(f"Time: {DDK_TRIAL_TIME} secs")
        self.syllable_text.SetLabel(f"Syllable: {self.syllable}")
        self.trial_text.SetLabel(f"Trial # {self.trial_number_}")
        self.syllable_video_title.SetLabel(f"Syllable ({self.syllable}) Instructions:")
        self.start_video_button.Enable(True)
        
        
        