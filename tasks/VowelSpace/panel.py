import wx
from panels.TrialPanel import TrialPanel
import logging
logger = logging.getLogger(__name__) # Or logging.getLogger() for the root logger
logger.setLevel(logging.DEBUG)


class VowelSpacePanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tap_hand = None
        self.repeat = True
        self.seconds = 0
        self.trial_number = 0
        self.timestamps ={}
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_vs(), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)
        self.SetSizerAndFit(vertical_sizer)
        
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)

        
    def _setup_vs(self):
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        self.current_text = wx.StaticText(self, label="")
        self.current_text.Wrap(299)
        
        self.finish_text = wx.StaticText(self, label="")
        
        self.finish_text.Wrap(299)

        self.continue_button = wx.ToggleButton(self, label="Begin Trial")
        
        self.repeat_trial = wx.ToggleButton(self, label="Repeat Trial")
        
        self.repeat_trial.Enable(False)
        grid_sizer = wx.GridBagSizer(5, 6)
        
        grid_sizer.Add(self.trial_text, pos=(0, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        grid_sizer.Add(self.current_text, pos=(1, 0), span=(0,6), flag=wx.ALIGN_LEFT  | wx.ALL, border=5)
        
        grid_sizer.Add(self.finish_text, pos=(2, 0), span=(0,6), flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        grid_sizer.Add(self.repeat_trial, pos=(3,0), span=(0,2), flag=wx.ALIGN_LEFT  | wx.TOP, border=5)  
        grid_sizer.Add(self.continue_button, pos=(3,2), span=(0,2), flag=wx.ALIGN_LEFT  | wx.TOP, border=5)  
        return grid_sizer
    
    
    def continue_event(self, event):
        self.rest_timer.Stop()
        self.continue_button.SetValue(True)
        self.repeat_trial.Enable(False)
    

    def is_finish(self):
        self.finish_text.SetLabel("Task Finished! Press End Task.")
    
        
    def repeat_event(self):
        self.repeat= True
        self.rest_timer.Stop()
        self.continue_button.SetValue(True)
        self.repeat_trial.Enable(False)
    
    def get_result(self):
        return self.repeat
    
    def reset(self, number):
        self.timestamps = {}
        
    def run_trial(self, count):
        self.repeat = False
        self.continue_button.SetLabel("Stop Trial")
        self.repeat_trial.Enable(False)
        
    def on_timer(self, event):
        self.seconds+=1
        
        
    def update_trial(self, trial, syllable):
        '''
        Updating with the current syllable
        Trials are 0-indexed so we add 1 here to be in a better format for showing
        '''
        
        self.current_text.SetLabel(f"Say {syllable} again")
        self.trial_text.SetLabel(f"Trial # {trial+1}")
            
    
    def start_new_trial(self):
        self.repeat = True
        self.repeat_trial.Enable(False)
        self.continue_button.Enable(True)
        self.finish_text.SetLabel("")
    
    
    
    
    