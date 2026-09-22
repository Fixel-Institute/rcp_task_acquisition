import ast
import json
import math
import time
from enum import Enum
from multiprocessing import Process
from queue import Empty

import rcp_task_acquisition.utils.file_utils as files
from rcp_task_acquisition.tasks.bases import StimulusBase
from rcp_task_acquisition.tasks.Diadochokinesis.Diadochokinesis import Diadochokinesis
from rcp_task_acquisition.tasks.HardwareTest import HardwareTest
from rcp_task_acquisition.tasks.NaturalisticSpeech.NaturalisticSpeech import NaturalisticSpeech
from rcp_task_acquisition.tasks.ContinuousRecording.ContinuousRecording import ContinuousRecording
from rcp_task_acquisition.tasks.NBack.NBack import N_back
from rcp_task_acquisition.tasks.ReachGrasp.ReachGrasp import ReachGrasp
from rcp_task_acquisition.tasks.Sara.Sara import Sara
from rcp_task_acquisition.tasks.ToneTaps.ToneTaps import ToneTapsClosed
from rcp_task_acquisition.tasks.UpdrsTap.BasicTaps import BasicTaps
from rcp_task_acquisition.tasks.VerbalFluency.VerbalFluency import VerbalFluency
from rcp_task_acquisition.tasks.VerbGeneration.VerbGeneration import VerbGeneration
from rcp_task_acquisition.tasks.OculoStim.OculoStim import OculoStim
from rcp_task_acquisition.tasks.MSITBD2.MSITBD2 import MSITBD2
from rcp_task_acquisition.tasks.VowelSpace.VowelSpace import VowelSpace
from rcp_task_acquisition.utils.displays import Window
from rcp_task_acquisition.utils.logger import get_logger

logger = get_logger("./models/StimulusThread")


class Msg(str, Enum):
    INITIALIZE = "init_stimulus"
    UPDATE_TASK = "update_task"
    RUN_TASK = "run_stimulus"
    END_TASK = "end_stimulus"
    ADD_INSTRUCTIONS = "create_instructions"  # unused
    PLAY_INSTRUCTIONS = "play_instructions"
    UPDATE_DATA = "update_data"
    RESET_TASK = "reset_task"
    HARDWARE_TEST = "hardware_test"
    CLOSE_WINDOW = "close"
    VOWEL_SPACE = "vowel_space"
    SEND_METADATA = "send_metadata"


class StimulusThread(Process):
    def __init__(
        self,
        msgq,
        finish,
        shared,
        frame,
        screen_config,
        task,
        button,
        press_count,
        video_status,
        resultsq,
        stimulus_timer,
        event_lock,
    ):
        super().__init__()
        self.msgq = msgq
        self.screenConfig = screen_config
        self.shared = shared
        self.finish = finish
        self.frame = frame
        self.button = button
        self.sess_path = ""
        self.stimulusConfig = files.get_stimulus_config("taskconfig.yaml")
        self.totalStimFrames = 0
        self.stimulus = None
        self.resultsq = resultsq
        self.press_count = press_count
        self.video_status = video_status
        self.timer = stimulus_timer
        self.alive = True
        self.task = task
        self.video_lock = event_lock
        

    def run(self):
        self.window = Window(screen=self.screenConfig, fullScreen=True)

        while self.alive:
            try:
                msg = self.msgq.get(timeout=0.05)
                logger.debug(f"msg: {msg}")
            except Empty:
                continue
            try:
                if msg == Msg.INITIALIZE:
                    self.params = {}
                    if len(msg.split("|")) > 1:
                        self.sess_path = msg.split("|")[1]
                    else:
                        self.sess_path = ""
                    self.init_stimuli()
                elif msg == Msg.SEND_METADATA:
                    self.send_metadata()
                elif msg == Msg.UPDATE_TASK:
                    msg = self.msgq.get()
                    self.task = msg
                elif msg == Msg.RUN_TASK:
                    self.shared.value = 0
                    # Main loop for presenting stimuli
                    tStart = time.time()
                    logger.info(f"Presenting {self.task}")

                    #self.stimulus.present_prep()
                    #results = self.stimulus.saveMetadata(self.stimulusConfig[self.task], None)
                    #json_str = json.dumps(results)
                    #self.resultsq.put(json_str)

                    if self.shared.value == -1:
                        break
                    self.stimulus.set_first_frame(self.frame.value)
                    self.window.reset_stimulus_frame()
                    self.stimulus.present()
                    self.window.idle(time_list=[])
                    self.window.flip()
                    self.totalStimFrames += self.window.stimulus_frame
                    self.window.reset_stimulus_frame()

                    tEnd = time.time()
                    tElapsed = tEnd - tStart
                    minutes = math.floor(tElapsed / 60)
                    seconds = tElapsed % 60
                    min_string = f"{math.floor(tElapsed / 60)} minutes, " if minutes > 0 else ""
                    logger.info(f"Stimulus protocol completed in {min_string}{seconds:.2f} seconds")
                    if self.finish.value != 2:
                        self.finish.value = 1
                    else:
                        self.finish.value = 0
                elif msg == Msg.END_TASK:
                    self.end_stimulus()
                elif msg == Msg.PLAY_INSTRUCTIONS:
                    msg = self.msgq.get()
                    logger.debug(msg)
                    self.play_video(msg)
                elif msg == Msg.ADD_INSTRUCTIONS:
                    msg = self.msgq.get()
                    self.setup_videos(msg)
                    # self.setup_videos(video_filename_dict)
                elif msg == Msg.HARDWARE_TEST:
                    base_vars = {
                        "display": self.window,
                        "frame": self.frame,
                        "timer": self.timer,
                        "video_lock": self.video_lock,
                        "video_status": self.video_status,
                        "finish": self.finish,
                    }
                    HardwareTest(base_vars).present()
                elif msg == Msg.UPDATE_DATA:
                    msgq_data = self.msgq.get()
                    logger.debug(f"stim: {msgq_data}")
                    try:
                        logger.debug(f"stimthread datadata: {msgq_data[0]}")
                        if msgq_data[0] == "(":
                            trial_data = ast.literal_eval(msgq_data)
                        else:
                            trial_data = msgq_data
                    except:
                        trial_data = msgq_data
                    # trial_data = trial_data.replace("(", "")
                    self.stimulus.update_data(trial_data)
                elif msg == Msg.RESET_TASK:
                    self.stimulus.reset_task()
                elif msg == Msg.VOWEL_SPACE:
                    results = self.stimulus.get_trial()
                    logger.debug(results)
                    self.resultsq.put(results)
                elif msg == Msg.CLOSE_WINDOW:
                    self.close_window()
            except SystemExit:
                logger.debug("interrupted stimulus")
                self.end_stimulus()
                # don't see which part of the code is supposed to raise SystemExit to reach here
                # also SystemExit is meant to exit the process. but this is continuing the main loop...
            except Exception as err:
                logger.exception("Error during main loop: %s", err)
                self.end_stimulus()
                break

    def init_stimuli(self):
        base_vars = {
            "display": self.window,
            "frame": self.frame,
            "timer": self.timer,
            "video_lock": self.video_lock,
            "video_status": self.video_status,
            "session_path": self.sess_path,
            "finish": self.finish,
        }
        logger.debug(f"base vars: {base_vars}")
        base_cls = dict(
            n_back=N_back,
            motor_task_finger_taps=BasicTaps,
            naturalistic_speech=NaturalisticSpeech,
            sara=Sara,
            diadochokinesis=Diadochokinesis,
            verbal_fluency=VerbalFluency,
            vowel_space=VowelSpace,
            reach_grasp=ReachGrasp,
            tone_taps_closed=ToneTapsClosed,
            verb_generation=VerbGeneration,
            continuous_recording=ContinuousRecording,
            oculostim_task=OculoStim,
            MSITBD2=MSITBD2,
        ).get(self.task, StimulusBase)
        #
        extra_args = []
        if self.task == "n_back":
            extra_args.append(self.button)
        elif self.task == "tone_taps_closed":
            extra_args.append(self.press_count)
            
        self.stimulus = base_cls(base_vars, *extra_args)
        logger.info(f"stimuli: {self.stimulus}")

    def end_stimulus(self):
        self.window.idle(time_list=[])
        # self.send_metadata()

    def send_metadata(self):
        # logger.debug(f"{self.stimulusConfig}, {self.task}, {self.stimulus}")
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

    def play_video(self, trial=None):
        if self.stimulus != None:
            self.stimulus.play_instructional_video(trial)
