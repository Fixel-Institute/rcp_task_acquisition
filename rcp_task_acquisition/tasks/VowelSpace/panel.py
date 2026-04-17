import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.VowelSpace.constants import VIDEO_PATHS
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panel/VowelSpace")



class VowelSpacePanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tap_hand = None
        self.repeat = True
        self.seconds = 0
        self.trial_number = 0
        self.timestamps ={}
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        static_box_sizer = self.setup_instruction_playback()
        vertical_sizer.Add(self._setup_vs(), 0, wx.ALIGN_LEFT | wx.ALL, 10)
        vertical_sizer.Add(self.add_video_panel(static_box_sizer), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizerAndFit(vertical_sizer)
        self.current_syllable = ""
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)
        self.instruction_paths = VIDEO_PATHS
        self.video_title.SetLabel("Instructions Overview: ")
        self.start_video_button.Enable(True)
        self.new_trial = False
        
    def _setup_vs(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        self.current_text = wx.StaticText(self, label="")
        self.current_text.Wrap(299)
        
        self.finish_text = wx.StaticText(self, label="")
        self.finish_text.Wrap(299)
        
        self.continue_button = wx.ToggleButton(self, label="Begin Trial")
        self.next_button = wx.Button(self, label="Next Trial")
        # self.next_button.Bind(wx.EVT_BUTTON, self.next_trial)
        
        grid_sizer = wx.GridBagSizer(5, 6)
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        grid_sizer.Add(self.current_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT  | wx.ALL, border=5)
        grid_sizer.Add(self.finish_text, pos=(2, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=5) 
        
        grid_sizer.Add(self.continue_button, pos=(3,0), span=(0,2), flag=wx.ALIGN_LEFT  | wx.TOP, border=5)  
        grid_sizer.Add(self.next_button, pos=(3,2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.TOP, border=5)  
        return grid_sizer
    
    
    def add_video_panel(self, static_box_sizer):
        self.syllable_video_title = wx.StaticText(self, label="Phrase Instructions:")
        self.syllable_start_video_button = wx.ToggleButton(self, label="Start Video", size=(self.button_width*2, -1))
        self.syllable_pause_video_button = wx.ToggleButton(self, label="Pause Video", size=(self.button_width*2, -1))
        self.syllable_pause_video_button.Enable(False)
        
        grid_sizer = wx.GridBagSizer(3,2)
        grid_sizer.Add(self.syllable_video_title, pos=(0, 0), span=(0,2), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.syllable_start_video_button, pos=(1, 0), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.syllable_pause_video_button, pos=(1, 1), span=(0,1), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)

        static_box_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, self.border)
        return static_box_sizer
    
    
    def continue_event(self, event):
        self.rest_timer.Stop()
        self.continue_button.SetValue(True)
        # self.repeat_trial.Enable(False)
    

    def is_finish(self):
        # self.finish_text.SetLabel("Task Finished! Press End Task.")
        self.finish_text.SetLabel("Task Finished! Press 'End Task' to save data.")
        # self.seconds_text.SetLabel("")
        self.current_text.SetLabel("")
        self.trial_text.SetLabel("")
        self.continue_button.Enable(False)
        self.next_button.Enable(False)
        self.syllable_video_title.SetLabel("Phrase Instructions:")
        self.syllable_start_video_button.Enable(False)
        
    def repeat_event(self):
        self.repeat= True
        self.rest_timer.Stop()
        self.continue_button.SetValue(True)

        # self.repeat_trial.Enable(False)
    
    def get_result(self):
        return  True #self.repeat
    
    def reset(self, number):
        self.timestamps = {}
        
    def run_trial(self, count):
        # self.repeat = False
        self.repeat = True
        self.continue_button.SetLabel("Stop Trial")
        self.next_button.Enable(False)
        
    def on_timer(self, event):
        self.seconds+=1
        
        
    def update_trial(self, trial, syllable):
        '''
        Updating with the current syllable
        Trials are 0-indexed so we add 1 here to be in a better format for showing
        '''
        self.current_text.SetLabel(f"Say {syllable} again")
        self.trial_text.SetLabel(f"Trial # {int(trial)+1}")
        self.current_syllable = syllable
        self.trial_number = int(trial)
        self.syllable_video_title.SetLabel(f"Phrase Instructions: {self.current_syllable}")
         
    def get_instruction(self, count):
        if self.syllable_start_video_button.GetValue():
            value =  self.current_syllable
        else:
            value = "introduction"
        return value
    
    
    def start_new_trial(self):
        self.repeat = True
        # self.repeat_trial.Enable(False)
        self.continue_button.Enable(True)
        self.finish_text.SetLabel("")
    

    def get_buttons(self):
        if self.syllable_start_video_button.GetValue():
            self.video_buttons = [self.syllable_start_video_button, self.syllable_pause_video_button]
            self.other_buttons = [self.start_video_button, self.pause_video_button]
        elif self.start_video_button.GetValue():
            self.video_buttons = [self.start_video_button, self.pause_video_button]
            self.other_buttons = [self.syllable_start_video_button, self.syllable_pause_video_button]

        
        
    def start_video(self):
        self.get_buttons()
        # self.next_button.Enable(False)
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
        
        # self.next_button.Enable(True)
        self.continue_button.Enable(True)
    
    
    def pause_video(self):
        self.video_buttons[1].SetLabel("Resume Video")
    
    
    def resume_video(self):
        self.video_buttons[1].SetLabel("Pause Video")
        
        
    # def next_trial(self, event):
    #     if self.trial_number < len(self.param_list):
    #         self.syllable = self.param_list[self.trial_number_]
    #         self.syllable_text.SetLabel(f"Syllable: {self.syllable}")
    #         self.continue_button.SetLabel("Begin Trial")
    #         self.trials[f"trial_{self.trial_number}"] = str(self.syllable)
    #         self.trial_number_+=1
    #         self.trial_text.SetLabel(f"Trial # {self.trial_number_}")
    #         self.syllable_video_title.SetLabel(f"Syllable ({self.syllable}) Instructions:")
    #     else:
    #         self.syllable_text.SetLabel("Task Finished! Press 'End Task' to save data.")
    #         self.seconds_text.SetLabel("")
    #         self.trial_text.SetLabel("")
    #         self.continue_button.Enable(False)
    #         self.next_button.Enable(False)
        