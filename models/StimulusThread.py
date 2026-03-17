import threading
import ctypes
import time
import math
import utils.file_utils as files
from tasks.UpdrsTap.BasicTaps import BasicTaps
from utils.displays import Window
from tasks.NaturalisticSpeech.NaturalisticSpeech import NaturalisticSpeech
from tasks.Diadochokinesis.Diadochokinesis import Diadochokinesis
from tasks.VerbalFluency.VerbalFluency import VerbalFluency
from tasks.VowelSpace.VowelSpace import VowelSpace
from tasks.NBack.NBack import N_back
from tasks.ReachGrasp.ReachGrasp import ReachGrasp
from tasks.ToneTaps.ToneTaps import ToneTapsClosed
from tasks.Sara.Sara import Sara
from tasks.HardwareTest import HardwareTest
from tasks.VerbGeneration.VerbGeneration import VerbGeneration
from tasks.bases import StimulusBase
from utils.logger import get_logger
from queue import Empty
logger = get_logger("./models/StimulusThread") 




class StimulusThread(threading.Thread):
    def __init__(self, msgq, finish, shared, frame, time, calculating_time, 
                 screen_config, task, button, show_panel, press_count, video_status):
        threading.Thread.__init__(self)
        self.msgq = msgq
        self.screenConfig = screen_config
        self.shared = shared
        self.finish = finish
        self.count = 1
        self.frame = frame
        self.time = time
        self.button = button
        self.calculating_time = calculating_time
        self.sessionFolder = None
        self.stimulusConfigFilename = "taskconfig.yaml"
        self.stimulusConfig = files.get_stimulus_config(self.stimulusConfigFilename)
        self.totalStimFrames = 0
        self.task = task
        self.params = {}
        self.stimulus = None
        self.show_panel = show_panel
        self.press_count = press_count
        self.loaded_video= None
        self.video_status = video_status
        self.alive = True
           
    
            
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
                if msg=="init_stimulus":
                    self.params = {}
                    self.init_stimuli()
                elif msg=="run_stimulus":
                    # time.sleep(5)
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
                elif "get_filename" in msg:
                     self.stimulusConfigFilename = msg.split(":")[1] + ".yaml"
                elif "play_instructions" in msg:
                    msg = self.msgq.get()
                    self.play_video(msg)
                elif "create_instructions" in msg:
                    msg = self.msgq.get()
                    self.setup_videos(msg)
                    # self.setup_videos(video_filename_dict)
                elif "hardware_test" in msg:
                    HardwareTest(self.window, self.finish, self.frame, self.video_status).present()
                else:
                    if self.task == "naturalistic_speech":
                        self.stimulus.update_photo(msg)
                    else:
                        self.stimulus.get_choices(msg)
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
            self.stimulus = VowelSpace(self.window, self.frame, self.finish)
        
        elif self.task == "reach_grasp":
            self.stimulus = ReachGrasp(self.window, self.frame, self.finish)
        
        elif self.task == 'tone_taps_closed':
            self.stimulus = ToneTapsClosed(self.window, self.frame, self.press_count, self.finish)
        
        elif self.task == "verb_generation":
            self.stimulus = VerbGeneration(self.window, self.frame, self.finish)
        
        else:
            self.stimulus = StimulusBase(self.window, self.frame, None, self.finish)
            
        logger.info(f"iterable: {self.stimulus}")
            
        
    def end_stimulus(self):
        self.window.idle(time_list = [])
        if hasattr(self.stimulus, 'saveMetadata'):
            
            self.params = self.stimulus.saveMetadata(self.stimulusConfig[self.task], self.sessionFolder)
        
        self.stimulus_iterable = []
        self.time.value = 0
        self.calculating_time.value = True
        
    def reset_count(self):
        self.count = 1
        
    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id
    
    
    def close_window(self):
        self.alive = False
        self.window.close()
        
        
    def get_sess_dir(self, sessionFolder):
        self.sessionFolder = sessionFolder
    
    def get_total_stim_flips(self):
        if self.window.stimulus_frame != 0:
            self.totalStimFrames+= self.window.stimulus_frame
        return self.totalStimFrames
    
    
    def get_params(self):
        return self.params
    
    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id),
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), 0)
            logger.info('Stimulus thread exception raised')

    
    def setup_videos(self, video_filename_dict):
        self.stimulus.setup_videos(video_filename_dict)
        

    def play_video(self, trial=None):
        if self.stimulus != None:
            self.stimulus.play_instructional_video(trial)


