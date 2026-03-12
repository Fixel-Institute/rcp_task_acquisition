# -*- coding: utf-8 -*-

from multiprocessing import Value
import wx
import wx.lib.dialogs
import os
import sys
import numpy as np
import time, datetime
import ctypes
import shutil
import queue
import multiCam_DLC.multiCam_DLC_utils_v2 as clara
from utils.file_utils import read_config
from models.StimulusThread import StimulusThread
from models.LabjackFrontend import LabjackFrontend
from models.Crop import Crop
from panels.GraphPanel import GraphPanel
from models.Warnings import Warning
from panels.MetadataPanel import MetadataPanel
from utils.constants import RAW_DATA_DIR, PLOT_LENGTH
from utils.stimulus_utils import thread_event
from utils.logger import get_logger
logger = get_logger("./multiCam_DLC_videoAcquisition_v1") 
from panels.ControlsPanel import ControlsPanel
from panels.ImagePanel import ImagePanel
from models.Serial import Serial
from models.CameraFrontend import Camera


class Trials():
    def __init__(self):
        self.trial_num = 0
        self.trial_button = 0
        pass
    
    def run_task(self, event):
        self.Enable()
        if self.task_button.GetValue():
            self.trial_dict = {}
            self.start_time= str(f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}Z') 
            self.count = 0
            self.thread.reset_count()
            self.finish.value = 0
            self.msgq.put("init_stimulus")
            self.create_file()
            is_success = self.lj.start_labjack()
            self.rest_timer.Start(1000)
            if not is_success:
                self.task_button.SetValue(False)
                return
            
            self.labjack_stream_button.SetValue(True)
            self.labjack_stream_button.Enable(False)
            self.labjack_stream_button.SetLabel("Stop Labjack")
            self.date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
            lj_path = os.path.join(self.sess_dir, f"{self.date_string}_{self.user_cfg['unitRef']}_{self.sess_string}_labjack.txt")
            msg = f"P{self.date_string}_{self.user_cfg['unitRef']}_{self.sess_string}x"
            self.lj.add_csv(lj_path, self.serial.serSuccess, self.serial.ser, msg)
            self.startingSession = True
            self.task_button.SetLabel("End Task")
            self.hardware_button.Enable(False)
            if self.task != "verbal_fluency":
                self.setup_videos()
            if self.task == "vowel_space":
                trial, syllable, finish = self.thread.stimulus.get_trial()
                self.trial_panel.repeat = True
                self.trial_panel.update_trial(trial, syllable)
            self.trial_panel.start_new_trial()
            self.trial_panel.show()
        else:
            if self.trial_button.GetValue():
                self.trial_button.SetValue(False)
                self.trial_event(event)
            if self.recording:
                self.cams.stop_recording(event)
            self.video_status.value = 4
            self.task_button.SetLabel("Start Task")
            self.hardware_button.Enable(True)
            self.trial_panel.hide()
            self.msgq.put('end_stimulus')
            self.labjack_scan_rate = self.lj.stop_labjack()
            self.thread.stimulus.close_audio()
            
            self.finish.value = 0
            self.labjack_stream_button.Enable(True)
            if self.labjack_stream_button.GetValue():
                self.labjack_stream_button.SetValue(False)
                self.labjack_stream_button.SetLabel("Stream Labjack")
            self.labjack_stream_button.Enable(True)
            self.end_time= str(f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}Z') 
            self.add_metadata()
            self.thread.stimulus.reset_task()
            self.labjack_timer.Start(200)

    def trial_event(self, event):
        if self.trial_button.GetValue():
            self.count +=1
            self.rest_timer.Start(1000)
            
            try:
                self.thread.stimulus.update_data(self.trial_panel.get_result())
            except:
                self.results_list.append(self.trial_panel.get_result())
            if self.task == "vowel_space":
                trial, syllable, finish = self.thread.stimulus.get_trial()
                self.trial_panel.update_trial(trial, syllable)
                if finish:
                   self.trial_button.Enable(True) 
            if self.task== "verbal_fluency" and self.trial_panel.first:
                self.count =0
                self.trial_button.SetLabel("Start Trial")
                self.trial_panel.switch_panel()
                
                self.thread.stimulus.update_data(self.trial_panel.get_result())
                self.results_list.append(self.trial_panel.get_result())
                self.setup_videos()
                return
                   
            self.trial_panel.run_trial(self.count)
            self.trial_button.SetLabel("Stop Trial")
            self.cams.start_recording(event, self.base_dir, self.sess_dir, self.user_cfg['unitRef'], self.sess_string, self.count)
            self.liveTimer.Start(150)
            self.msgq.put("run_stimulus")

            # # elif self.task == "reach_grasp":
            # #     self.trial_panel.run_trial(self.count)
            # #     # hand, grasp_object = self.trial_panel.get_result()
            # #     # self.thread.stimulus.update_values(hand, grasp_object)
            # #     # self.trial_button.SetLabel("Stop Trial")
            # #     # self.cams.start_recording(event, self.base_dir, self.sess_dir, self.user_cfg['unitRef'], self.sess_string, self.count)
            # #     # self.liveTimer.Start(150)
            # #     # self.msgq.put("run_stimulus")

            # else:
            #     self.trial_panel.run_trial(self.count)
            #     self.results_list.append(self.trial_panel.get_result())
            #     # self.trial_button.SetLabel("Stop Trial")
            #     # self.cams.start_recording(event, self.base_dir, self.sess_dir, self.user_cfg['unitRef'], self.sess_string, self.count)
            #     # self.liveTimer.Start(150)
            #     # self.msgq.put("run_stimulus")
        else:
            if (self.task == "naturalistic_speech" or 
                self.task == "reach_grasp"):
                thread_event.set()
                self.msgq.put("end_stimulus")
                self.cams.stop_recording(event)
                self.trial_button.SetLabel("Begin Trial")
                self.trial_panel.reset(self.count)
                self.trial_panel.end_trial()
                self.stimulus_panel.value = False
                self.finish.value = 0
                self.liveTimer.Stop()
                return
            elif self.task == "sara":
                thread_event.set()
                self.trial_panel.show_scoring()
            elif self.task == "vowel_space":
                thread_event.set()
                trial, syllable, finish = self.thread.stimulus.get_trial()
                if finish:
                    self.trial_panel.is_finish()
                    self.trial_button.Enable(False)
                    self.trial_button.SetLabel("Next Trial")
                    self.trial_panel.repeat_trial.Enable(True)    
                    self.trial_panel.repeat_trial.SetValue(False) 
                    self.cams.stop_recording(event)
                    self.liveTimer.Stop()
                    return
                self.trial_panel.repeat_trial.Enable(True)
                self.trial_panel.repeat_trial.SetValue(False)
            elif self.task == "verbal_fluency":
                
                self.finish.value = 2
                self.trial_panel.update_values()
                self.trial_button.SetLabel("Start Trial")
                self.trial_button.seconds = 0
                self.cams.stop_recording(event)
                self.trial_panel.reset(self.count)
                self.trial_panel.end_trial()
                self.stimulus_panel.value = False
                self.liveTimer.Stop()
                return
            self.finish.value = 2
            self.msgq.put("end_stimulus")
            self.cams.stop_recording(event)
            self.trial_button.SetLabel("Begin Trial")
            self.trial_panel.reset(self.count)
            self.trial_panel.end_trial()
            self.liveTimer.Stop()
        
        
    def setup_videos(self): 
        video_paths = self.trial_panel.get_instructions()
        self.msgq.put("create_instructions")
        self.msgq.put(video_paths)
        
        
    def repeat_event(self, event):
        self.trial_panel.repeat_event()
        self.trial_event(event)
        

    def update_intertrial(self, event):
        if self.video_status.value == 5:
            self.trial_panel.stop_video()
            self.video_status.value = 0
        elif (self.finish.value == 1 and 
        (self.task != "naturalistic_speech" and self.task != "vowel_space")):
            self.cams.stop_recording(event)
            self.trial_panel.reset(self.count)
            self.trial_panel.end_trial()
            self.stimulus_panel.value = False
            self.finish.value = 0
            if self.task == "verbal_fluency":
                self.trial_panel.update_values()
                self.trial_button.SetLabel("Start Trial")
                self.trial_button.seconds = 0


    def play_instructions(self, event):
        if event.GetEventObject().GetValue():
            if type(self.trial_panel.get_instructions()) is str:
                result = ""
            else:
                result = self.trial_panel.get_result()
            self.msgq.put("play_instructions")
            self.msgq.put(result)
            self.trial_panel.start_video()
            self.video_status.value = 1
        else:
            self.video_status.value = 4
            self.trial_panel.stop_video()
        
        
    def pause_instructions(self, event):
        if event.GetEventObject().GetValue():
            self.video_status.value = 2
            self.trial_panel.pause_video()
        else:
            self.video_status.value = 3
            self.trial_panel.resume_video()