# -*- coding: utf-8 -*-
from psychopy import core

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/Sara")



# Sets up display window, fixation cross, text pages and image stimuli
class Sara(bases.StimulusBase):
    def __init__(self, base_vars):
        super().__init__(**base_vars)
        self.trial =0
        
    def present(self, test=True):
        self.timer.value = 0
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        clock = core.Clock()
        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()
            self.timer.value = int(clock.getTime())
        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.play_tone()
        
        
    def saveMetadata(self, name, sessionFolder):
        data = None
        return data
    