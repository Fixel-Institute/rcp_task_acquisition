# -*- coding: utf-8 -*-
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel



class ReachGraspPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reach_hand = "Left"
        self.pace = "Self-Paced"
        self.grasp_object = "Large"
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_fingertap(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)


        
    def _setup_fingertap(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        
        self.hand_text = wx.StaticText(self, label='Choose which hand trial will use:')
        self.left_radio = wx.RadioButton(self, label="Left Hand", style= wx.RB_GROUP)
        self.right_radio = wx.RadioButton(self, label="Right Hand")
        # self.left_radio.Bind(wx.EVT_RADIOBUTTON, self.on_select)
        # self.right_radio.Bind(wx.EVT_RADIOBUTTON, self.on_select)
        
        self.object_text = wx.StaticText(self, label='Choose grasp apparatus:')
        self.large_object_radio = wx.RadioButton(self, label="Large", style= wx.RB_GROUP)
        self.precision_object_radio = wx.RadioButton(self, label="Precision")
        
        self.seconds_text = wx.StaticText(self, label= "Time: 0 secs")
        
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
    
        grid_sizer = wx.GridBagSizer(6, 4)
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.left_radio, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.right_radio, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.object_text, pos=(3, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.large_object_radio, pos=(4, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.precision_object_radio, pos=(4, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(5, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(6, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer
    
    def run_trial(self, number):
        self.seconds = 0
        self.left_radio.Enable(False)
        self.right_radio.Enable(False)
        self.hand_text.Enable(False)
        self.object_text.Enable(False)
        self.large_object_radio.Enable(False)
        self.precision_object_radio.Enable(False)
        self.trial_text.SetLabel(f"Trial # {number}")
        self.trial_is_active = True
    
    def continue_event(self, event):
        self.rest_timer.Stop()
    
        
    def get_result(self):
        # self.pace = "Self-Paced" if self.self_radio.GetValue() else "Fast As Possible"
        self.grasp_object = "Large" if self.large_object_radio.GetValue() else "Precision"
        self.reach_hand = "Left" if self.left_radio.GetValue() else "Right"
        return f"{self.reach_hand},{self.grasp_object}" #, self.pace
        
    def cancel_event(self, event):
        self.cancel = True
        self.rest_timer.Stop()
    

    def reset(self, number):
        self.seconds = 5
        self.left_radio.Enable(True)
        self.right_radio.Enable(True)
        self.hand_text.Enable(True)
        self.object_text.Enable(True)
        self.large_object_radio.Enable(True)
        self.precision_object_radio.Enable(True)
        self.seconds_text.SetLabel(f"Time: 0 secs")
        self.continue_button.SetValue(False)
        self.continue_button.SetLabel("Begin Trial")
        self.trial_text.SetLabel(f"Trial # {number+1}")
    
    

        
    def on_timer(self, event):
        if self.trial_is_active:
            self.seconds+=1
            self.seconds_text.SetLabel(f"Time: {self.seconds} secs")

