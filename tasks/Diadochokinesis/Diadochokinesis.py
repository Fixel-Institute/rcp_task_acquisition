# -*- coding: utf-8 -*-
from psychopy import core #, visual
from tasks import bases
# from utils.logging import logger
from tasks.Diadochokinesis.constants import DDK_TRIAL_TIME
import logging
# Get a logger instance (or the root logger)
logger = logging.getLogger(__name__) # Or logging.getLogger() for the root logger
logger.setLevel(logging.DEBUG)


# Parameters
PARAMS = {
    "trials_per_syllable": 3, 
    "syllable_list" : ["puh", "tuh", "kuh", "puhtuhkuh", "butterfly"],
    "time_per_trial": 10
    }



class Diadochokinesis(bases.StimulusBase):
    def __init__(self, window, frame, is_finished, video_status):
        super().__init__(window, frame, video_status)
        self.finish = is_finished
        self.round = 0
        self.trial_count = 0
        self.syllable = None
        self.index = None
        self.repeat = None 
        self.rest = False
        self.trial_dict = {}
        
        
    def present(self):
        self.trial_count+=1
        PARAMS[f"trial_{self.trial_count}"] = self.repeat
        self.play_tone()
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        
        clock = core.Clock() 
        while clock.getTime() < DDK_TRIAL_TIME:
            
            self.display.draw_patch()
            self.display.flip()
            if self.finish.value == 2:
                break
            
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
    
    def get_trial(self):
        next_syllable = self.syllable
        if self.trial_count == 3:
            if self.index < len(PARAMS["syllable_list"]) - 1:
                #not the end of the list
                next_syllable = PARAMS["syllable_list"][self.index+1]
            else:
                next_syllable = None
        return self.trial_count, self.syllable, next_syllable
       
        
    def update_data(self, data):
        self.repeat = data
        
        
    def saveMetadata(self, name, sessionFolder):
        return PARAMS
            
