# -*- coding: utf-8 -*-
from psychopy import core

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.tasks.Diadochokinesis.constants import (DDK_TRIAL_TIME,
                                                                  DDK_PATHS, 
                                                                  DDK_TRIALS_PER_SYLLABLE, 
                                                                  DDK_TRIALS)
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/Diadochokinesis") 


class Diadochokinesis(bases.StimulusBase):
    def __init__(self, window, frame, video_status, is_finished):
        super().__init__(window, frame, is_finished, video_status)
        self.round = 0
        self.trial_count = 0
        self.syllable = None
        self.index = None
        self.repeat = None 
        self.rest = False
        self.trial_dict = {}
        self.instructions_dict = DDK_PATHS
        
        
    def present(self):
        self.trial_count+=1
        self.trial_dict[f"trial_{self.trial_count}"] = self.repeat
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
            if self.index < len(DDK_TRIALS) - 1:
                #not the end of the list
                next_syllable = DDK_TRIALS[self.index+1]
            else:
                next_syllable = None
        return self.trial_count, self.syllable, next_syllable
       
        
    def update_data(self, data):
        self.repeat = data
        
        
    def saveMetadata(self, name, sessionFolder):
        params = {
               "trials_per_syllable": DDK_TRIALS_PER_SYLLABLE, 
               "syllable_list" : DDK_TRIALS,
               "time_per_trial": DDK_TRIAL_TIME
               }
        logger.debug(self.trial_dict)
        params["trials"] = self.trial_dict
        return params
            
