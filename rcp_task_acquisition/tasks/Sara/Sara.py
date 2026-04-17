# -*- coding: utf-8 -*-
from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/Sara")



# Sets up display window, fixation cross, text pages and image stimuli
class Sara(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame)

        self.finish = finish
        self.trial =0
        
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
        self.play_tone()
        
        
    def saveMetadata(self, name, sessionFolder):
        data = None
        return data
    