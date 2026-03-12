from psychopy import core, sound #, visual
from tasks import bases
# from utils.logging import logger
from  utils.stimulus_utils import thread_event
from tasks.UpdrsTap.constants import BASIC_TAPS_TIME
import logging
# Get a logger instance (or the root logger)
logger = logging.getLogger(__name__) # Or logging.getLogger() for the root logger
logger.setLevel(logging.DEBUG)


# Parameters
PARAMS = {
    "time_per_trial": 10, 
    "number_of_trials": 0,
    "hand_used": {}
    }


class BasicTaps(bases.StimulusBase):
    def __init__(self, window, frame, is_finished, video_status):
        super().__init__(window, frame, video_status)
        self.finish = is_finished
        self.trial_count = 0
        self.hand= None
        
        
    def present(self):
        self.trial_count+=1
        PARAMS["hand_used"][f"trial_{self.trial_count}"] = self.hand
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
        clock = core.Clock()   
        while clock.getTime() < BASIC_TAPS_TIME:
            self.display.flip()
            if self.finish.value == 2:
                break
            
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone() 
        
       
    def update_data(self, hand):
        self.hand = hand
        
        
    def saveMetadata(self, name, sessionFolder):
        PARAMS["number_of_trials"] = self.trial_count
        return PARAMS
            
            