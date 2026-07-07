import os
from psychopy import visual, core
from PIL import Image

from rcp_task_acquisition.tasks.NaturalisticSpeech.constants import IMG_DIR
from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/NaturalisticSpeech") 



# Sets up display window, fixation cross, text pages and image stimuli
class NaturalisticSpeech(bases.StimulusBase):
    def __init__(self, base_vars):
        super().__init__(**base_vars)
        self.photo = None
        self.photo_dict = {}
        self.trial =0
        self.screen_width = 2200 #not technically screen width but we dont want to cover the photodiode
        self.screen_height = 1440
        
    def present(self, test=True):
        # Load and draw the photo being presented
        self.timer.value = 0
        if not self.photo:
            logger.warn("No Photo is selected")
            return
        
        self.trial+=1
        logger.debug(self.photo)
        
        with Image.open(self.photo) as img:
            width, height = img.size
            logger.debug(f"Width: {width}, Height: {height}")
        new_height = (self.screen_width/width)*height
        new_width = self.screen_width
        if new_height > self.screen_height:
            new_width = (self.screen_height/height)*width
            new_height = self.screen_height
        logger.debug(f"width: {new_width}, height: {new_height}")
        self.photo_dict[f"trial_{self.trial}"] = self.photo
        stim = visual.ImageStim(self.display, image=self.photo, name=self.photo, size=[new_width, new_height], units='pix')
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        stim.draw()
        self.display.flip()
        
        clock = core.Clock()
        while self.finish.value == 0:
            stim.draw()
            self.display.draw_patch()
            self.display.flip()
            self.timer.value = int(clock.getTime())
        
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