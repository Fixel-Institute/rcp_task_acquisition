from psychopy import core, sound #, visual
from tasks import bases
# from utils.logging import logger
from  utils.stimulus_utils import thread_event
import logging
# Get a logger instance (or the root logger)
logger = logging.getLogger(__name__) # Or logging.getLogger() for the root logger
logger.setLevel(logging.DEBUG)


# Parameters
PARAMS = {
    "number_of_trials": 0,
    "hand_used": {},
    "grasp_object": {}
    }


class ReachGrasp(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame)
        self.trial_count = 0
        self.hand = None
        self.grasp_object = None
        self.finish = finish
        
    def present(self):        
        self.trial_count+=1
        PARAMS["hand_used"][f"trial_{self.trial_count}"] = self.hand
        PARAMS["grasp_object"][f"trial_{self.trial_count}"] = self.grasp_object
        self.play_tone()
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()

        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()        

        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()        
        self.play_tone()

        
        
    def update_data(self, data):
        self.hand = data[0]    
        self.grasp_object = data[1]   
                 
        
    def saveMetadata(self, name, sessionFolder):
        PARAMS["number_of_trials"] = self.trial_count
        return PARAMS
            
            