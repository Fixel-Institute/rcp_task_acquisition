# -*- coding: utf-8 -*-
import wx
import json

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.VerbalFluency.constants import (PHONEMIC_LIST, 
                                                                SEMANTIC_LIST,
                                                                PHONEMIC_PHRASE, 
                                                                SEMANTIC_PHRASE)
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/VerbalFluencyPanel") 


class VerbalFluencyPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompt = None
        self.type = None
        self.first = True
        self.value = None
        self.trial_num = 0
        self.actual_list = []
        self.phonemic_list = None
        self.initial_list = None
        self.semantic = None
        self.trial_is_active = False
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_panel(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)  
        vertical_sizer.Add(self.setup_instruction_playback(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)


    def _setup_panel(self):
        self.phonemic_task = wx.StaticText(self, label='Choose Phonemic Category:')
        self.initial_list = PHONEMIC_LIST
        self.phonemic_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=self.initial_list,
                                       size=(200, -1))
        
        self.semantic_task = wx.StaticText(self, label="Choose Semantic Category:")
        self.semantic_list = SEMANTIC_LIST
        self.semantic_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=self.semantic_list,
                                       size=(200, -1))
        
        self.continue_button= wx.ToggleButton(self, label="Begin Task", size=(150, -1))
        
        self.prompt_text = wx.StaticText(self, label= "", size=(300, 50))
        self.seconds_text = wx.StaticText(self, label= "", size=(300, -1))

        grid_sizer = wx.GridBagSizer(7, 6)
        grid_sizer.Add(self.phonemic_task, pos=(0, 0), span=(0, 2),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.phonemic_choice, pos=(1, 0), span=(0, 4),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.semantic_task, pos=(2, 0), span=(0, 2),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.semantic_choice, pos=(3, 0), span=(0,4),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.seconds_text, pos=(4, 0), span=(0,4),  flag= wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.prompt_text, pos=(5, 0), span=(0,5),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(7, 0), span=(0, 3),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        return grid_sizer
    
    
    def switch_panel(self):
        self.phonemic_choice.Enable(False)
        self.semantic_choice.Enable(False)
        self.semantic_task.Enable(False)
        self.phonemic_task.Enable(False)
        self.seconds = 0
        self.seconds_text.SetLabel("Time: 60 secs")
        self.phonemic_list = json.loads(self.initial_list[self.phonemic_choice.GetSelection()])
        self.semantic = self.semantic_list[self.semantic_choice.GetSelection()]
        logger.debug(f"Trial Continued; {self.phonemic_list}, {self.semantic} selected")
        self.value = self.phonemic_list[self.trial_num]
        self.prompt_text.SetLabel(PHONEMIC_PHRASE.replace("*", self.value))
        self.video_title.SetLabel(f"Trial: {self.value}")
        self.prompt_text.Wrap(299)
        self.continue_button.SetValue(False)
        self.first = False
        self.Layout()
        self.Update()
        
        logger.debug(f"value: {self.value}")
        self.trial_num+=1
        self.actual_list.append(self.value)
        self.start_video_button.Enable(True)


    def update_values(self):
        self.continue_button.SetValue(False)
        self.start_video_button.Enable(True)
        self.seconds_text.SetLabel("Time: 60 secs")
        if self.trial_num < len(self.phonemic_list):
            self.value = self.phonemic_list[self.trial_num]
            self.prompt_text.SetLabel(PHONEMIC_PHRASE.replace("*", self.value))
            self.prompt_text.Wrap(299)
            logger.debug(f"value: {self.value}")
        elif self.trial_num == len(self.phonemic_list):
            self.value = self.semantic
            self.prompt_text.SetLabel(SEMANTIC_PHRASE.replace("*", self.value))
            self.value = self.semantic
            self.prompt_text.Wrap(299)
        else:
            self.prompt_text.SetLabel("Task Finished!\n Press 'End Task' button to save data.")
            self.selections = 0
            self.first = True
            self.seconds_text.SetLabel(" ")
            self.continue_button.Enable(False)
            self.start_video_button.Enable(False)
        self.trial_num +=1
        self.actual_list.append(self.value)
        self.video_title.SetLabel(f"Trial: {self.value}")
        self.start_video_button.SetValue(False)
        self.start_video_button.SetLabel("Play Video")

        
    def get_result(self):
        return self.value
    
    
    def get_instruction(self, count):
        return self.value
    
    
    def cancel_event(self, event):
        self.cancel = True


    def reset(self, trial):
        super().reset(trial)
        self.continue_button.Enable(True)
    
    
    def add_metadata(self):
        return {"phonemic_category": self.phonemic_list,
                "semantic_category": self.semantic}
  
    
    def on_timer(self, event):
        if self.trial_is_active:
            self.seconds-=1
            if self.seconds >= 0:
                self.seconds_text.SetLabel(f"Time: {self.seconds} secs")


    def run_trial(self, count):
        self.seconds = 60
        super().start_trial()

        
    def get_trials(self):
        return f"{'.'.join(self.phonemic_list)},{self.semantic},{self.value}"
    
    
    def start_new_trial(self):
        super().start_new_trial()        
        self.trial_num = 0
        self.phonemic_choice.Enable(True)
        self.semantic_choice.Enable(True)
        self.semantic_task.Enable(True)
        self.phonemic_task.Enable(True)
        self.seconds = 0
        self.first = True
        self.prompt_text.SetLabel("")
        self.seconds_text.SetLabel("")
        self.continue_button.Enable(True)
        self.continue_button.SetLabel("Begin Task")
        self.video_title.SetLabel("")
        self.start_video_button.SetValue(False)
        self.start_video_button.SetLabel("Play Video")
        self.start_video_button.Enable(False)
        self.Layout()
        self.Update()