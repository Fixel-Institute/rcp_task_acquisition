from tasks import bases
import numpy as np
import os
from  tasks.VowelSpace import constants as c
from utils.logger import get_logger
logger = get_logger("./tasks/VowelSpace") 



class VowelSpace(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame)
        self.generated_trials = None
        self.completed_trials_dict = {}
        self.create_trial_data()
        self.repeat_num = 0
        self.finish = finish
        self.is_finished = False
      
        
    def present(self):
        
        self.current_trial =str(self.generated_trials[self.trial])
        self.completed_trials_dict[f"trial_{self.trial+self.repeat_num}"] = str(self.current_trial)
        logger.debug(f"trial: {self.trial}, repeat: {self.repeat_num}, current: {self.current_trial}")
        
        self.trial_bookends()
        self.play_vowel_phrase(str(self.current_trial))
        
        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()

        # thread_event.wait()
        # thread_event.clear()
        self.trial_bookends()



    def get_trial(self):
        if self.trial >= (len(self.generated_trials)-1):
            self.is_finished=True
        return self.trial, self.generated_trials[self.trial], self.is_finished
    
    
    def update_data(self, is_repeated):
        if is_repeated:
            self.repeat_num+=1
        else:
            self.trial+=1
            if self.trial >= len(self.generated_trials)-1:
                self.is_finished = True
        
        
    def create_trial_data(self):
        num_repeats = int(c.VS_NUM_TRIALS/len(c.PHRASE_LIST))
        new_trials = np.tile(c.PHRASE_LIST, num_repeats)
        np.random.shuffle(new_trials)
        self.generated_trials = new_trials.tolist()


    def saveMetadata(self, name, sessionFolder):
        metadata = { "trial_list": self.generated_trials,
                     "trial_number": c.VS_NUM_TRIALS,
                     "trial_data": self.completed_trials_dict
                     }
        return metadata


    def reset_task(self):
        self.trial = 0
        self.repeat_num = 0
        self.is_finished = False
        self.create_trial_data()


    def play_vowel_phrase(self, trial):
        '''
        set up and play the files for the current phrase.
        one con of this method is there is no way (I know of) to stop in the
        middle of the file. So if someone is quickly clicking through data will 
        be dropped.'''
        
        logger.debug(trial)
        try:
            file = c.VS_PATHS[trial]
            path =  os.path.join(c.STIM_DIR, file)
            os.system(f'play -q {path} vol {c.VOLUME}')
        except:
            logger.warn("No file, continuing without....")
        

