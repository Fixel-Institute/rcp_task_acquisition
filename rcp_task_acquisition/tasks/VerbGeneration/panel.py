# -*- coding: utf-8 -*-
import wx
import csv

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
import rcp_task_acquisition.tasks.VerbGeneration.constants as c
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./VerbGeneration/panel") 



class VerbGenerationPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seconds = 0
        self.display_secs = 0
        self.display_mins = 0
        self.trial_number = 1
        self.timestamps ={}
        self.countdown_start = 0
        self.button_width = 76
        self.border = 5
        self.selection = 0
        self.verb_lists =[]
        with open(c.CSV_PATH, "r") as f:
            reader = csv.reader(f, delimiter=",")
            for i, line in enumerate(reader):
                list_str= f"{line[0]}: [{', '.join(line[1:7])}...]"
                self.verb_lists.append(list_str)
                
        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._set_up_photo(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)
     

    def _set_up_photo(self):
        '''
        Set up the naturalistic speech panel
        Returns:
            message (wx dialog panel)

        '''
        noun_text = wx.StaticText(self, label='Choose List:')
        self.noun_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=self.verb_lists,
                                       size=(310, -1))
        self.noun_choice.SetSelection(self.selection)
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        self.seconds_text = wx.StaticText(self, label= "Time: 0 mins, 0 secs")
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
        
        grid_sizer = wx.GridBagSizer(5, 4)
        grid_sizer.Add(self.trial_text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(noun_text, pos=(2, 0), span=(0,4), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
        grid_sizer.Add(self.noun_choice, pos=(3, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(4, 0), span=(0, 4), flag=wx.ALIGN_LEFT |  wx.ALL, border=10)
        grid_sizer.Add(self.continue_button, pos=(5, 0), span=(0, 4), flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        return grid_sizer


    def run_trial(self, number):
        self.seconds = 0
        self.trial_number = number
        self.trial_is_active = True
        self.noun_choice.Enable(False)
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")


    def update_trial(self, number):
        self.trial_number = number
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")
        
        
    def get_result(self):
        list_choice = self.noun_choice.GetSelection()
        return list_choice

    
    def reset(self, number):
        self.seconds = 0
        self.trial_number = number
        self.trial_is_active = False
        self.seconds_text.SetLabel("Time: 0 mins, 0 secs")
        self.noun_choice.Enable(True)
        # self.shown_image.Enable(True)
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")
        self.continue_button.SetValue(False)
        
        
    def on_timer(self, event):
        self.seconds+=1
        self.display_mins = int(self.seconds/60)
        self.display_secs = self.seconds%60
        if self.trial_is_active:
            self.seconds_text.SetLabel(f"Time: {self.display_mins} mins, {self.display_secs} secs")



