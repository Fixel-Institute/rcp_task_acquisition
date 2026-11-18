# -*- coding: utf-8 -*-
# ============================================================
# CHANGE LOG
#   11.18.26: one-click block buttons (Calibrate, Saccades,
#             Smooth Pursuit, Fixation). Each one selects its
#             paradigm and presses Begin Trial for you, so the
#             block starts through MainFrame.trial_event exactly
#             as before (cameras, OpenIris, photodiode, metadata
#             unchanged). The radio buttons + Begin Trial still
#             work. While a block runs, all block buttons and
#             radio buttons are disabled; Begin Trial becomes
#             Stop Trial as before.
#   11.18.26: "Run Gaze Calibration" radio is now disabled
#             during a block and re-enabled after, like the
#             others (it was left enabled).
#   Every changed line is marked with its date below. The
#   original file is panel_before_buttons.py.
# ============================================================
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
        self.calibration_radio = wx.RadioButton(self, label="Run Gaze Calibration")
        
        self.seconds_text = wx.StaticText(self, label= "Time: 0 secs")
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))

        # 11.18.26: added - one-click block buttons. Each selects its
        # radio button, then presses Begin Trial (see _start_block).
        self.block_text = wx.StaticText(self, label="Or start a block directly:")
        self.block_buttons = {}
        for name, radio in [("Calibrate", self.calibration_radio),
                            ("Saccades", self.saccade_radio),
                            ("Smooth Pursuit", self.pursuit_radio),
                            ("Fixation", self.fixation_radio)]:
            b = wx.Button(self, label=name, size=(self.button_width*2, -1))
            b.Bind(wx.EVT_BUTTON, lambda event, r=radio: self._start_block(r))
            self.block_buttons[name] = b
    
        grid_sizer = wx.GridBagSizer(6, 6)
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.saccade_radio, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.pursuit_radio, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.fixation_radio, pos=(2, 4), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        grid_sizer.Add(self.calibration_radio, pos=(3, 4), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(4, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(5, 0), span=(0,3), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)

        # 11.18.26: added - block buttons below Begin Trial, two per row
        grid_sizer.Add(self.block_text, pos=(6, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        for k, b in enumerate(self.block_buttons.values()):
            grid_sizer.Add(b, pos=(7 + k // 2, 3 * (k % 2)), span=(0,3), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer

    # 11.18.26: added
    def _start_block(self, radio):
        """
        Select the paradigm and press Begin Trial. MainFrame binds
        EVT_TOGGLEBUTTON on continue_button to trial_event, so
        posting that event starts the block the same way a click
        on Begin Trial does.
        """
        if self.trial_is_active or self.continue_button.GetValue():
            return                          # a block is already running
        radio.SetValue(True)
        self.continue_button.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_TOGGLEBUTTON, self.continue_button.GetId())
        evt.SetEventObject(self.continue_button)
        evt.SetInt(1)
        wx.PostEvent(self.continue_button.GetEventHandler(), evt)

    # 11.18.26: added - enable/disable every way of picking a block
    def _enable_choices(self, on):
        for w in (self.saccade_radio, self.pursuit_radio, self.fixation_radio, self.calibration_radio):
            w.Enable(on)
        for b in self.block_buttons.values():
            b.Enable(on)

    def run_trial(self, number):
        self.seconds = 0
        self._enable_choices(False)          # 11.18.26: was saccade/pursuit/fixation radios only
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
        elif self.calibration_radio.GetValue():
            self.selection = "Calibration"
        return "OculoStim",self.selection,self.trial_number

    def reset(self, number):
        self.seconds = 5
        self._enable_choices(True)           # 11.18.26: was saccade/pursuit/fixation radios only
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


