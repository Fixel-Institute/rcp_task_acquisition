import os
import numpy as np
import simpleaudio as sima

from rcp_task_acquisition.tasks import bases
from  rcp_task_acquisition.tasks.VowelSpace import constants as c
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/VowelSpace") 



class VowelSpace(bases.StimulusBase):
    def __init__(self, window, frame, finish, video_status):
        super().__init__(window, frame, video_status, finish)
        self.generated_trials = None
        self.completed_trials_dict = {}
        self.create_trial_data()
        self.repeat_num = 0
        self.is_finished = False
        self.actual_trials = 0
        self.instructions_dict = c.VIDEO_PATHS
      
        
    def present(self):
        self.current_trial =str(self.generated_trials[self.trial])
        self.actual_trials+=1
        self.completed_trials_dict[f"trial_{self.actual_trials}"] = str(self.current_trial)
        logger.debug(f"trial: {self.trial}, repeat: {self.repeat_num}, current: {self.current_trial}")
        
        self.trial_bookends()
        self.play_vowel_phrase(str(self.current_trial))
        
        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()

        self.trial_bookends()


    def get_trial(self):
        logger.debug(self.trial)
        logger.debug(self.generated_trials)
        logger.debug(len(self.generated_trials))
        if self.trial > (len(self.generated_trials)):
            self.is_finished=True
        if self.is_finished:
            return f"-1,-1,{self.is_finished}"
        return f"{self.trial},{self.generated_trials[self.trial]},{self.is_finished}"
    
    
    def update_data(self, is_repeated):
        is_repeated = is_repeated[0] == "True"
        if is_repeated:
            # self.repeat_num+=1
            logger.debug("in is_repeated")
        else:
            logger.debug("in is_updated")
            self.trial+=1
            if self.trial >= len(self.generated_trials):
                self.is_finished = True
        
        
    def create_trial_data(self):
        num_repeats = int(c.VS_NUM_TRIALS/len(c.PHRASE_LIST))
        new_trials = np.tile(c.PHRASE_LIST, num_repeats)
        np.random.shuffle(new_trials)
        self.generated_trials = new_trials.tolist()
        logger.debug(f'trial: {self.generated_trials}')


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
            wave_obj = sima.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
    
            # Wait until playback finishes
            play_obj.wait_done()
        except:
            logger.warn("No file, continuing without....")
        

