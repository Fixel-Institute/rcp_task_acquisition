# -*- coding: utf-8 -*-
from psychopy import core
from tasks import bases
from utils.logger import get_logger
logger = get_logger("./tasks/VerbalFluency") 
from tasks.VerbalFluency.constants import TRIAL_TIME 

# Parameters
PARAMS = {
    "time_per_trial": TRIAL_TIME
    }



class VerbalFluency(bases.StimulusBase):
    def __init__(self, window, frame, finished, video_status):
        super().__init__(window, frame, video_status)
        self.trial_num = 0 
        self.trial_type = None
        self.trial_name = None
        self.finish = finished
        
        
    def present(self):
        self.trial_num+=1
        PARAMS[f"trial_{self.trial_num}"] = self.trial
        
        self.play_tone()
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        
        clock = core.Clock()   
        while clock.getTime() < TRIAL_TIME:
            self.display.draw_patch()
            self.display.flip()
            if self.finish.value == 2:
                break
            
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone() 

    def update_data(self, choices):
        print(choices)
        self.trial = choices
        
    def get_trial(self):
        return self.trial, self.trial_type, self.trial_name
        
    def saveMetadata(self, name, sessionFolder):
        return PARAMS
    


            