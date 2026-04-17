# -*- coding: utf-8 -*-
import wx

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/TrialPanel") 



class TrialPanel(wx.Panel):
    def __init__(self, parent=None):
        self.seconds = 0
        self.trial_number = 0
        self.countdown_start = 0
        self.button_width = 76
        self.border = 5
        self.trial_is_active = False
        self.instruction_paths = {}
        
        # so there is no error for tasks without videos
        self.start_video_button = None
        self.pause_video_button = None
        self.video_title = None
        
        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_buttons(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)

        
    def _setup_buttons(self):
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(150, -1))
        self.repeat_trial = wx.ToggleButton(self, label="Repeat Trial", size=(150, -1))
        grid_sizer = wx.GridBagSizer(0,0)
        self.continue_button.Hide()
        self.repeat_trial.Hide()
        grid_sizer.Add(self.continue_button, pos=(0, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.repeat_trial , pos=(1, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer
    
    
    def setup_instruction_playback(self):
        self.video_title = wx.StaticText(self, label="")
        self.start_video_button = wx.ToggleButton(self, label="Play Video", size=(150, -1))
        self.pause_video_button = wx.ToggleButton(self, label="Pause Video", size=(150, -1))
        self.pause_video_button.Enable(False)
        self.start_video_button.Enable(False)
        grid_sizer = wx.GridBagSizer(3,2)
    
        grid_sizer.Add(self.video_title, pos=(0, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.start_video_button, pos=(1, 0), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.pause_video_button, pos=(1, 1), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)

        static_box = wx.StaticBox(self, wx.ID_ANY, "Video Instructions")
        static_box_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        static_box_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 5)

        return static_box_sizer


    def reset(self, count):
        self.seconds = 0
    
    
    def show(self):
        self.rest_timer.Start(1000)
        self.Show()
    
    
    def hide(self):
        self.rest_timer.Stop()
        self.Hide()
       
    def start_trial(self):
        self.trial_is_active = True
        self.pause_video_button.Enable(False)
        self.start_video_button.Enable(False)
    
    def end_trial(self):
        self.trial_is_active = False
        if self.start_video_button != None:
            self.start_video_button.Enable(True)
        
    def get_video_buttons(self):
        return self.start_video_button, self.pause_video_button
    
    def start_video(self):
        self.start_video_button.SetLabel("Stop Video")
        self.pause_video_button.Enable(True)
    
    def stop_video(self):
        self.start_video_button.SetLabel("Start Video")
        self.start_video_button.SetValue(False)
        if self.pause_video_button.GetValue():
            self.pause_video_button.SetValue(False)
            self.pause_video_button.Enable(False)
            self.pause_video_button.SetLabel("Pause Video")
    
    def pause_video(self):
        self.pause_video_button.SetLabel("Resume Video")
    
    def resume_video(self):
        self.pause_video_button.SetLabel("Pause Video")
        
    def run_trial(self, count):
        pass
    
    def get_result(self):
        return None
    
    def on_timer(self, event):
        pass


    def get_instructions(self):
        return self.instruction_paths
        
    def start_new_trial(self):
        self.trial_number = 0
        
    def update_values(self):
        pass
