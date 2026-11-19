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
#   11.18.26 (later): the radio buttons are removed; the four
#             block buttons are the only way to pick a block.
#             The chosen block is kept in self.selection (was
#             read from the radios). Begin Trial is hidden until
#             a block runs, and then shows as "Stop Block" to end
#             it early. A label shows which block is running.
#   11.19.26: Calibrate split into "Calibrate (online)" (trial
#             type "Calibration", online with offline fallback)
#             and "Calibrate (offline)" (trial type
#             "CalibrationOffline", old timed 9-dot routine only).
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
        self.selection = "Saccade"     # 11.18.26: was "" (the Saccade radio was selected by default)
        self.image_list = []

        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))

        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_oculostim_controls(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)

    def _setup_oculostim_controls(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        
        # 11.18.26: removed the paradigm radio buttons ('Choose which
        # paradigm to run:'); the block buttons below replace them.
        self.hand_text = wx.StaticText(self, label="Start a block:")      # 11.18.26: was 'Choose which paradigm to run:'
        
        self.seconds_text = wx.StaticText(self, label= "Time: 0 secs")
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
        self.continue_button.Hide()         # 11.18.26: added - shown only while a block runs (as "Stop Block")
        self.block_status = wx.StaticText(self, label="No block running")  # 11.18.26: added

        # 11.18.26: added - one-click block buttons. Each sets the
        # selection, then presses Begin Trial (see _start_block).
        self.block_buttons = {}
        for name, selection in [("Calibrate (online)", "Calibration"),           # 11.19.26: was "Calibrate"
                                ("Calibrate (offline)", "CalibrationOffline"),  # 11.19.26: added
                                ("Saccades", "Saccade"),
                                ("Smooth Pursuit", "Pursuit"),
                                ("Fixation", "Fixation")]:
            b = wx.Button(self, label=name, size=(self.button_width*2, -1))
            b.Bind(wx.EVT_BUTTON, lambda event, s=selection, n=name: self._start_block(s, n))
            self.block_buttons[name] = b
    
        grid_sizer = wx.GridBagSizer(6, 6)
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        # 11.18.26: block buttons, two per row from row 2 (11.19.26: rows follow the button count)
        for k, b in enumerate(self.block_buttons.values()):
            grid_sizer.Add(b, pos=(2 + k // 2, 3 * (k % 2)), span=(0,3), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        r = 2 + (len(self.block_buttons) + 1) // 2     # 11.19.26: first free row (was fixed at 4)
        grid_sizer.Add(self.block_status, pos=(r, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)  # 11.18.26: added
        grid_sizer.Add(self.seconds_text, pos=(r + 1, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(r + 2, 0), span=(0,3), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        return grid_sizer

    # 11.18.26: added
    def _start_block(self, selection, name):
        """
        Set the block and press Begin Trial. MainFrame binds
        EVT_TOGGLEBUTTON on continue_button to trial_event, so
        posting that event starts the block the same way a click
        on Begin Trial does.
        """
        if self.trial_is_active or self.continue_button.GetValue():
            return                          # a block is already running
        self.selection = selection          # 11.18.26: was radio.SetValue(True)
        self.continue_button.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_TOGGLEBUTTON, self.continue_button.GetId())
        evt.SetEventObject(self.continue_button)
        evt.SetInt(1)
        wx.PostEvent(self.continue_button.GetEventHandler(), evt)

    # 11.18.26: added - enable/disable the block buttons; the Stop
    # button is shown only while a block runs
    def _enable_choices(self, on):
        for b in self.block_buttons.values():
            b.Enable(on)
        self.continue_button.Show(not on)
        if on:
            self.block_status.SetLabel("No block running")
        else:
            names = {"Calibration": "Calibrate (online)", "CalibrationOffline": "Calibrate (offline)",  # 11.19.26: offline added
                     "Saccade": "Saccades",
                     "Pursuit": "Smooth Pursuit", "Fixation": "Fixation"}
            self.block_status.SetLabel(f"Running: {names.get(self.selection, self.selection)}")
            # MainFrame labels it "Stop Trial" right after run_trial
            wx.CallAfter(self.continue_button.SetLabel, "Stop Block")
        self.Layout()

    def run_trial(self, number):
        self.seconds = 0
        self._enable_choices(False)          # 11.18.26: was saccade/pursuit/fixation radios only (radios now removed)
        self.trial_text.SetLabel(f"Trial # {number}")
        self.trial_is_active = True
    
    def update_trial(self, number):
        self.trial_number = number
        
    def get_result(self):
        # 11.18.26: selection is set by the block button (was read from the radios)
        return "OculoStim",self.selection,self.trial_number

    def reset(self, number):
        self.seconds = 5
        self._enable_choices(True)           # 11.18.26: was saccade/pursuit/fixation radios only (radios now removed)
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


