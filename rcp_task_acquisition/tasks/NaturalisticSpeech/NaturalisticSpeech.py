import os
from psychopy import visual

from rcp_task_acquisition.tasks.NaturalisticSpeech.constants import IMG_DIR
from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/NaturalisticSpeech") 



# Sets up display window, fixation cross, text pages and image stimuli
class NaturalisticSpeech(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame, None, finish)
        self.photo = None
        self.photo_dict = {}
        self.trial =0
        
        
    def present(self, test=True):
        # Load and draw the photo being presented
        if not self.photo:
            logger.warn("No Photo is selected")
            return
        
        self.trial+=1
        logger.debug(self.photo)
        self.photo_dict[f"trial_{self.trial}"] = self.photo
        stim = visual.ImageStim(self.display, image=self.photo, name=self.photo, size=[1200, 1200], units='pix')
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        stim.draw()
        self.display.flip()
        
        while self.finish.value == 0:
            stim.draw()
            self.display.draw_patch()
            self.display.flip()
        
        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
        
    def saveMetadata(self, name, sessionFolder):
        # data = {"photo_paths": self.photo_dict}
        # logger.debug(data)
        return self.photo_dict
    
    
    def update_data(self, trial_data):
        photo = trial_data[0]
        self.photo = os.path.join(IMG_DIR, photo)