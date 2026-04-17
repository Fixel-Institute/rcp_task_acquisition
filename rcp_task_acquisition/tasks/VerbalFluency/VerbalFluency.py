# -*- coding: utf-8 -*-
from psychopy import core

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.tasks.VerbalFluency.constants import TRIAL_TIME, VERBAL_FLUENCY_PATHS
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/VerbalFluency") 



class VerbalFluency(bases.StimulusBase):
    def __init__(self, window, frame, finished, video_status):
        super().__init__(window, frame, video_status, finished)
        self.trial_num = 0 
        self.trial_type = None
        self.trial_name = None
        self.trial_dict = {}
        self.phonemic_list = []
        self.semantic = None
        
        
    def present(self):
        self.trial_num+=1
        self.trial_dict[f"trial_{self.trial_num}"] = self.trial
        
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
        if len(choices) == 1:
            if choices[0] == 'None':
                return
            else:
                self.trial = choices[0]
                return
        logger.debug(choices)
        self.phonemic_list = choices[0].split(".")
        self.semantic = choices[1]
        self.trial = choices[2]
        self.instructions_dict = VERBAL_FLUENCY_PATHS[choices[0]]
        self.instructions_dict[self.semantic] = VERBAL_FLUENCY_PATHS["Semantic"][self.semantic]
        logger.debug(self.instructions_dict)
        
    def get_trial(self):
        return self.trial, self.trial_type, self.trial_name

        
    def saveMetadata(self, name, sessionFolder):
        data = { "time_per_trial": TRIAL_TIME,
                 "trials": self.trial_dict
            }
        return data
    
            