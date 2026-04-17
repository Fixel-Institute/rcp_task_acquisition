# -*- coding: utf-8 -*-
import wx
import wx.grid

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.Sara.constants import ASSESMENTS
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/SaraPanel") 



class SaraPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_assesment = None
        self.assesment_list = list(ASSESMENTS.keys())
        self.assesment_num = 0
        self.actual_assesments = {}
        self.recent_trials = {}
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_panel(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)  
        # vertical_sizer.Add(self.setup_instruction_playback(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        self.edit_num = None

        

    def _setup_panel(self):
        self.assesment_task = wx.StaticText(self, label='Choose Assesment:')
        self.assesment_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=self.assesment_list,
                                       size=(310, -1))
        
        self.continue_button= wx.ToggleButton(self, label="Begin Assesment", size=(150, -1))
        self.edit_button = wx.Button(self, label="Edit Previous Score", size=(150, -1))
        self.edit_button.Enable(False)
        self.seconds_text = wx.StaticText(self, label= "Time: 0 secs", size=(300, -1))
        self.assesment_choice.SetSelection(0)
        self.assesment_choice.Bind(wx.EVT_CHOICE, self.check_can_edit)
        grid_sizer = wx.GridBagSizer(7, 6)
        grid_sizer.Add(self.assesment_task, pos=(0, 0), span=(0, 2),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER | wx.ALL, border=5)
        grid_sizer.Add(self.assesment_choice, pos=(1, 0), span=(0, 4),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN  | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.seconds_text, pos=(2, 0), span=(0,4),  flag= wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.continue_button, pos=(3, 0), span=(0, 3),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        grid_sizer.Add(self.edit_button, pos=(3, 3), span=(0, 3),  flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
        self.edit_button.Bind(wx.EVT_BUTTON, self.edit_score)
        return grid_sizer
    
    
    def show_scoring(self):
        self.scoring_panel = AssesmentPanel(self.current_assesment)
        self.scoring_panel.Bind(wx.EVT_CLOSE, self.reset_assesment)
        self.scoring_panel.continue_button.Bind(wx.EVT_BUTTON, self.reset_assesment)
        self.continue_button.Enable(False)
        self.edit_button.Enable(False)
        
        
    def add_metadata(self):
        return self.actual_assesments
        
    
    def reset_assesment(self, event):
        
        button, text = self.scoring_panel.Destroy()
        logger.debug(f"button: {button}, text: {text}")
        assesment_dict = {
            "type": self.current_assesment,
            "score": button,
            "description": ASSESMENTS[self.current_assesment][button],
            "notes": text
            }
        self.assesment_num = self.assesment_choice.GetSelection()
        if self.assesment_num < len(self.assesment_list)-1:
            self.assesment_num+=1
        else:
            self.assesment_num = 0
        self.current_assesment = self.assesment_list[self.assesment_num]
        self.assesment_choice.SetSelection(self.assesment_num)
        logger.debug(f"edit num: {self.edit_num}")
        if self.edit_num != None:
            self.actual_assesments[f"{self.edit_num}"] = assesment_dict
            self.edit_num = None
        else:
            self.actual_assesments[f"trial_{self.trial_number}"] = assesment_dict
        self.assesment_task.Enable(True)
        self.assesment_choice.Enable(True)
        self.continue_button.SetLabel("Begin Assesment")
        self.continue_button.Enable(True)
        self.seconds_text.SetLabel("Time: 0 secs")
        self.check_can_edit(event)
        
        
    def get_result(self):
        return self.current_assesment
        
    
    def cancel_event(self, event):
        self.cancel = True


    def run_trial(self, event):
        self.trial_number+=1
        logger.debug(f"trial Number: {self.trial_number}")
        self.trial_is_active = True
        self.assesment_task.Enable(False)
        self.assesment_choice.Enable(False)
        self.current_assesment = self.assesment_list[self.assesment_choice.GetSelection()]
        self.continue_button.SetLabel("End Assesment")
        self.recent_trials[self.current_assesment] = self.trial_number
    

    def check_can_edit(self, event):
        self.assesment_num = self.assesment_choice.GetSelection()
        self.current_assesment = self.assesment_list[self.assesment_num]
        if self.assesment_list[self.assesment_num] in self.recent_trials.keys():
            self.edit_button.Enable(True)
        else:
            self.edit_button.Enable(False)


    def reset(self, trial):
        super().reset(trial)
        self.continue_button.Enable(True)
    

    def on_timer(self, event):
        if self.trial_is_active:
            self.seconds+=1
            if self.seconds >= 0:
                self.seconds_text.SetLabel(f"Time: {self.seconds} secs")


    def edit_score(self, event):
        logger.debug(f"assesment: {self.recent_trials[self.current_assesment]}")
        self.edit_num = f"trial_{self.recent_trials[self.current_assesment]}"
        args = self.actual_assesments[f"trial_{self.recent_trials[self.current_assesment]}"]
        logger.debug(f"actual a: {self.actual_assesments}")
        logger.debug(f"args: {args}")
        logger.debug(f"recent t: {self.recent_trials}")
        self.scoring_panel = AssesmentPanel(self.current_assesment, args)
        self.scoring_panel.Bind(wx.EVT_CLOSE, self.reset_assesment)
        self.scoring_panel.continue_button.Bind(wx.EVT_BUTTON, self.reset_assesment)
        self.continue_button.Enable(False)
        self.edit_button.Enable(False)





class AssesmentPanel(wx.Dialog):
    def __init__(self, current_assesment, args={}, parent=None):
        super().__init__(parent, title= 'Score Assesment')
        self.vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        self.border = 7
        self.left_radio = None
        self.button_list = {}
        self.vertical_sizer.Add(self._create_assesment_score(current_assesment, args), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.vertical_sizer.Add(self._add_notes(args), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.vertical_sizer.Add(self._add_buttons(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizerAndFit(self.vertical_sizer)
        self.Layout()
        self.Show()
        
        
    def _create_assesment_score(self, current_assesment, args={}):
        assesment_scores = ASSESMENTS[current_assesment]
        grid_sizer = wx.GridBagSizer(len(assesment_scores.keys()), 3)
        for assesment in assesment_scores:
            button = wx.RadioButton(self)
            number = wx.StaticText(self, label=str(assesment))
            self.button_list[assesment] = button
            description = wx.StaticText(self, label=assesment_scores[assesment])
            description.Wrap(520)
            grid_sizer.Add(button, pos=(assesment, 0), span=(0, 1),  flag= wx.ALIGN_LEFT | wx.ALL, border=self.border)
            grid_sizer.Add(number, pos=(assesment, 1), span=(0, 1),  flag= wx.ALIGN_LEFT | wx.ALL, border=self.border)
            grid_sizer.Add(description, pos=(assesment, 2), span=(0, 1),  flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        if "score" in args.keys():
            self.button_list[args["score"]].SetValue(True)
        return grid_sizer
    
    
    def _add_notes(self, args={}):
        grid_sizer = wx.GridBagSizer(2, 4)
        notes_text =  wx.StaticText(self, label='Notes:')
        self.notes = wx.TextCtrl(self, size=wx.Size(550, 100), style=wx.TE_MULTILINE | wx.TE_LEFT)
        grid_sizer.Add(notes_text, pos=(0,0), span=(0, 1),  flag= wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.notes, pos=(1,0), span=(0, 4),  flag= wx.ALIGN_LEFT | wx.ALL, border=self.border)
        if "notes" in args.keys():
            self.notes.SetValue(args["notes"])
        return grid_sizer
        
        
        grid_sizer = wx.GridBagSizer(2, 4)
        grid_sizer.Add(self.hand_text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.left_radio, pos=(2, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.right_radio, pos=(2, 2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.ALL, border=self.border)
        return grid_sizer
    
    def _add_buttons(self):
        grid_sizer = wx.GridBagSizer(1, 4)
        self.continue_button= wx.Button(self, label="Confirm Score", size=(150, -1))
        
        grid_sizer.Add(self.continue_button, pos=(0, 0), span=(0, 2),  flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
        return grid_sizer
    
    def Destroy(self):
        text = self.notes.GetValue()
        
        button_used = None
        for button in self.button_list:
            if self.button_list[button].GetValue():
                button_used = button
        logger.debug(f"button used: {button_used}")
        super().Destroy()
        return button_used, text
    
    