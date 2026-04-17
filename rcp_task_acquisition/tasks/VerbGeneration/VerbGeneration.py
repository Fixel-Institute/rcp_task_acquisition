# -*- coding: utf-8 -*-
import csv
from psychopy import visual,core

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
import rcp_task_acquisition.tasks.VerbGeneration.constants as c
logger = get_logger("./tasks/VerbGeneration") 



# Sets up display window, fixation cross, text pages and image stimuli
class VerbGeneration(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame)
        self.finished = finish
        self.list_num = None
        self.words_shown = []
        self.trial =0
        self.trial_list = {}
        self.lists = []
        self.stim_list = []
        self.fixation = visual.TextStim(self.display, text="+", name="FixationCross", pos=(0, 0), height=50)
        
        with open(c.CSV_PATH, "r") as f:
            reader = csv.reader(f, delimiter=",")
            for i, line in enumerate(reader):
                self.lists.append(line[1:])
        logger.debug(self.lists)
        
    def present(self, test=True):
        self.trial+=1
        self.words_shown = []
        self.play_tone()
        for index, stim in enumerate(self.stim_list):
            self.words_shown.append(self.lists[self.list_num][index])
            stim.draw()
            
            self.display.switch_patch()
            self.display.draw_patch()
            self.display.flip()
            clock = core.Clock()   
            while clock.getTime() < c.SHOW_TIME:    
                stim.draw()
                self.display.draw_patch()
                self.display.flip()
                if self.finished.value == 2:
                    self.display.switch_patch()
                    self.display.draw_patch()
                    self.display.flip()
                    self.trial_list[f"trial_{self.trial}"] = self.words_shown
                    return
    
            #turn the patch to off and flip the display to black
            self.display.switch_patch()
            self.display.draw_patch()
            clock = core.Clock()  
            while clock.getTime() < c.GENERATION_TIME:
                self.fixation.draw()
                self.display.flip()
                if self.finished.value == 2:
                    self.display.flip()
                    self.trial_list[f"trial_{self.trial}"] = self.words_shown
                    return
        self.trial_list[f"trial_{self.trial}"] = self.words_shown
        self.display.flip()
        
        
    def saveMetadata(self, name, sessionFolder):
        # data = {f"trial_{self.trial}": list(self.words_shown),
        #         "word_time": str(c.SHOW_TIME),
        #         "fixation_time": str(c.GENERATION_TIME)}
        self.trial_list["word_time"] = str(c.SHOW_TIME)
        self.trial_list["fixation_time"] = str(c.GENERATION_TIME)
        return self.trial_list
    
    
    def update_data(self, list_num):
        self.stim_list = []
        self.list_num = int(list_num[0])#-1
        for word in self.lists[self.list_num]:
            self.stim_list.append(visual.TextStim(self.display, text=word, name="trial", pos=(0, 0), height=100))
