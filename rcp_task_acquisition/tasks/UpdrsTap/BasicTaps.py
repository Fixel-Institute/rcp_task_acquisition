from psychopy import core

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.tasks.UpdrsTap.constants import BASIC_TAPS_TIME, BASIC_TAPS_PATH
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/UpdrsTap")



class BasicTaps(bases.StimulusBase):
    def __init__(self, window, frame, is_finished, video_status):
        super().__init__(window, frame, video_status,  is_finished)
        # self.finish = is_finished
        self.trial_count = 0
        self.hand= None
        self.hand_used = {}
        self.instructions_dict = BASIC_TAPS_PATH
        
    def present(self):
        self.trial_count+=1
        self.hand_used[f"trial_{self.trial_count}"] = self.hand
        self.display.switch_patch()
        
        self.display.flip()
        self.play_tone()
        
        clock = core.Clock()   
        while clock.getTime() < BASIC_TAPS_TIME:
            self.display.draw_patch()
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
        data = {
           "time_per_trial": BASIC_TAPS_TIME, 
           "number_of_trials": self.trial_count,
           "hand_used": self.hand_used
           }
        return data
            
            