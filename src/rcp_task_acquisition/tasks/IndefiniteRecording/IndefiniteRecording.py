from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/IndefiniteRecording") 

# Sets up display window, fixation cross, text pages and image stimuli
class IndefiniteRecording(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame, None, finish)
        self.trial = 0
        self.screen_width = 2200 #not technically screen width but we dont want to cover the photodiode
        self.screen_height = 1440
        
    def present(self, test=True):
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        
        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()
        
        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
    def saveMetadata(self, name, sessionFolder):
        return {}
    
    def update_data(self, trial_data):
        pass