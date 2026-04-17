import time
import math
from enum import Enum
from queue import Empty
import json
from multiprocessing import Process

import rcp_task_acquisition.utils.file_utils as files
from rcp_task_acquisition.tasks.UpdrsTap.BasicTaps import BasicTaps
from rcp_task_acquisition.utils.displays import Window
from rcp_task_acquisition.tasks.NaturalisticSpeech.NaturalisticSpeech import NaturalisticSpeech
from rcp_task_acquisition.tasks.Diadochokinesis.Diadochokinesis import Diadochokinesis
from rcp_task_acquisition.tasks.VerbalFluency.VerbalFluency import VerbalFluency
from rcp_task_acquisition.tasks.VowelSpace.VowelSpace import VowelSpace
from rcp_task_acquisition.tasks.NBack.NBack import N_back
from rcp_task_acquisition.tasks.ReachGrasp.ReachGrasp import ReachGrasp
from rcp_task_acquisition.tasks.ToneTaps.ToneTaps import ToneTapsClosed
from rcp_task_acquisition.tasks.Sara.Sara import Sara
from rcp_task_acquisition.tasks.HardwareTest import HardwareTest
from rcp_task_acquisition.tasks.VerbGeneration.VerbGeneration import VerbGeneration
from rcp_task_acquisition.tasks.bases import StimulusBase
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/StimulusThread") 


class Msg(Enum):
    INITIALIZE = "init_stimulus"
    UPDATE_TASK = "update_task"
    RUN_TASK = "run_stimulus"


class StimulusThread(Process):
    def __init__(self, msgq, finish, shared, frame, 
                 screen_config, task, button, press_count, video_status, resultsq):
        super().__init__()
        self.msgq = msgq
        self.screenConfig = screen_config
        self.shared = shared
        self.finish = finish
        self.frame = frame
        self.button = button
        self.stimulusConfig = files.get_stimulus_config("taskconfig.yaml")
        self.totalStimFrames = 0
        self.stimulus = None
        self.resultsq = resultsq
        self.press_count = press_count
        self.video_status = video_status
        self.alive = True  
        self.task = task
        
        
    def run(self):
        self.window = Window(
                    screen=self.screenConfig['screenNumber'],
                    fullScreen=self.screenConfig['fullScreen']
                    )

        while self.alive:
            try:
                msg = self.msgq.get(timeout=0.05)
                logger.debug(msg)
            except Empty:
                continue
            try:
                if msg == Msg.INITIALIZE.value:
                    self.params = {}
                    self.init_stimuli()
                elif msg == Msg.UPDATE_TASK.value:
                    msg= self.msgq.get()
                    self.task = msg
                elif msg == Msg.RUN_TASK.value:
                    self.shared.value = 0
                    # Main loop for presenting stimuli
                    tStart = time.time()
                    logger.info(f"Presenting {self.task}")
                    if self.shared.value == -1:
                        break
                    self.stimulus.set_first_frame(self.frame.value)  
                    self.window.reset_stimulus_frame()
                    self.stimulus.present()
                    self.window.idle(time_list = [])
                    self.window.flip()
                    self.totalStimFrames += self.window.stimulus_frame
                    self.window.reset_stimulus_frame()
                    
                    tEnd = time.time()
                    tElapsed = (tEnd - tStart) 
                    minutes = math.floor(tElapsed/ 60)
                    seconds = (tElapsed%60)
                    min_string = f"{math.floor(tElapsed/ 60)} minutes, " if minutes > 0 else ""
                    logger.info(f'Stimulus protocol completed in {min_string}{seconds:.2f} seconds')

                    self.finish.value = 1
                elif msg=="end_stimulus":
                    
                    self.end_stimulus()
                elif "play_instructions" in msg:
                    msg = self.msgq.get()
                    
                    logger.debug(msg)
                    self.play_video(msg)
                elif "create_instructions" in msg:
                    msg = self.msgq.get()
                    self.setup_videos(msg)
                    # self.setup_videos(video_filename_dict)
                elif "hardware_test" in msg:
                    HardwareTest(self.window, self.finish, self.frame, self.video_status).present()
                elif "update_data" in msg:
                    msgq_data = self.msgq.get()
                    logger.debug(f"stim: {msgq_data}")
                    try:
                        trial_data = msgq_data.split(',')
                    except:
                        trial_data = msgq_data
                    # trial_data = trial_data.replace("(", "")
                    self.stimulus.update_data(trial_data)
                elif "reset_task" in msg:
                    self.stimulus.reset_task()
                elif "vowel_space" in msg:
                    results = self.stimulus.get_trial()
                    logger.debug(results)
                    self.resultsq.put(results)
                elif "close" in msg:
                    self.close_window()
            except SystemExit:
                logger.debug("interrupted stimulus")
                self.window.idle(time_list = [])
                self.end_stimulus()
                
                
    def init_stimuli(self):
        if self.task == 'n_back':
            self.stimulus = N_back(self.window, self.frame, self.button, self.finish)

        elif self.task == 'motor_task_finger_taps':
            self.stimulus = BasicTaps(self.window, self.frame, self.finish, self.video_status)
        
        elif self.task == 'naturalistic_speech':
            self.stimulus = NaturalisticSpeech(self.window, self.frame, self.finish)
        
        elif self.task == "sara":
            self.stimulus = Sara(self.window, self.frame, self.finish)
        
        elif self.task == 'diadochokinesis':
            self.stimulus =Diadochokinesis(self.window, self.frame, self.finish, self.video_status)
            
        elif self.task == "verbal_fluency":
            self.stimulus = VerbalFluency(self.window, self.frame, self.finish, self.video_status)
        
        elif self.task == "vowel_space":
            self.stimulus = VowelSpace(self.window, self.frame, self.finish, self.video_status)
        
        elif self.task == "reach_grasp":
            self.stimulus = ReachGrasp(self.window, self.frame, self.finish)
        
        elif self.task == 'tone_taps_closed':
            self.stimulus = ToneTapsClosed(self.window, self.frame, self.press_count, self.finish, self.video_status)
        
        elif self.task == "verb_generation":
            self.stimulus = VerbGeneration(self.window, self.frame, self.finish)

        else:
            self.stimulus = StimulusBase(self.window, self.frame, None, self.finish)
            
        logger.info(f"iterable: {self.stimulus}")
            
        
    def end_stimulus(self):
        self.window.idle(time_list = [])
        if hasattr(self.stimulus, 'saveMetadata'):
            logger.debug(f"{self.stimulusConfig}, {self.task}, {self.stimulus}")
            results = self.stimulus.saveMetadata(self.stimulusConfig[self.task], None)
            json_str = json.dumps(results)
            logger.debug(f"jsonstr: {json_str}")
            self.resultsq.put(json_str)
    
    
    def close_window(self):
        self.alive = False
        self.window.close()
        # self.p.join()
        
    
    def get_params(self):
        return self.params

    
    def setup_videos(self, video_filename_dict):
        pass
        # self.stimulus.setup_videos(video_filename_dict)
        
        
        

    def play_video(self, trial=None):
        if self.stimulus != None:
            self.stimulus.play_instructional_video(trial)


