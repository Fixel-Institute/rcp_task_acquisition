# -*- coding: utf-8 -*-
import os
import time
import numpy as np
import shutil
import cv2
import ctypes
from multiprocessing import Queue, Value, Array
from dataclasses import dataclass

from rcp_task_acquisition.utils.constants import DOWNSAMPLE_VAL, CAM_MAX_WIDTH, CAM_MAX_HEIGHT
import rcp_task_acquisition.models.CameraProcess as spin
import rcp_task_acquisition.utils.file_utils as file_utils
from rcp_task_acquisition.models.Crop import Crop
from rcp_task_acquisition.models.Warnings import Warning
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/CameraFrontend") 


@dataclass
class FrameDims:
    x1: int
    x2: int
    y1: int
    y2: int
    h:  int
    w:  int
    dispSize: int

@dataclass
class CamSettings:
    name: str
    serial: str
    is_primary: bool
    size: int
    shape: list[int]
    bin_val: int
    frame_dims: list[int]
    decrease_val: int
    actual_framerate: None | float
    exposure: None | float
    cam_tests: np.ndarray
    contrast_tests: np.ndarray
    frame: np.ndarray
    frameBuff: np.ndarray
    array4feed: Array
    frmGrab: Value
    camq: None
    camq_p2read: None
    frame_size: None | FrameDims

 
class Camera():
    def __init__(self, serial, panel, image_panel, contrast_test, focus_test, monitor):
        self.serial = serial
        self.shared = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.reset_variables()
        self.dtype = 'uint8'
        self.cam_crop = Crop()
        self.ctrl_panel = panel
        self.image_panel = image_panel
        self.contrast_test = contrast_test
        self.focus_test= focus_test
        self.warning = Warning()
        self.unconnected = list()
        self.camStrList = list()
        self.cam_settings = list()
        self.trial = 0
        self.session = 0
        self.participant_monitor = monitor
        self.framerate = None


    def setup(self, config, is_unconnected, requested_framerate):
        self.cam_cfg = config
        self.cam_crop = Crop()
        self.framerate = requested_framerate
        self.reset_variables()
        self.cam_dict = {}
        
        for name in self.cam_cfg:
            if not self.cam_cfg[name]["in_use"]:
                continue
            
            else:
                cam_bin = int(self.cam_cfg[name]['bin'])
                cam_dims = [0,
                            int(CAM_MAX_HEIGHT/DOWNSAMPLE_VAL/cam_bin),
                            0,
                            int(CAM_MAX_WIDTH/DOWNSAMPLE_VAL/cam_bin)]
                is_primary = True if self.cam_cfg[name]['ismaster'] or is_unconnected else False
                new_cam = CamSettings(name = name,
                                      serial = self.cam_cfg[name]['serial'],
                                      is_primary = is_primary,
                                      size = cam_dims[1]*cam_dims[3]*3,
                                      shape = [cam_dims[1], cam_dims[3], 3],
                                      bin_val = cam_bin,
                                      frame_dims = cam_dims,
                                      decrease_val = int(self.cam_cfg[name]['framerate_decrease_factor']),
                                      actual_framerate = None,
                                      exposure = None,
                                      cam_tests = np.full(shape=30*2, fill_value=np.nan),
                                      contrast_tests = np.full(shape=30*2, fill_value=np.nan),
                                      frame= np.zeros([cam_dims[1], cam_dims[3], 3], dtype='ubyte'),
                                      frameBuff = np.zeros(cam_dims[1]*cam_dims[3]*3, dtype='ubyte'),
                                      array4feed = Array(ctypes.c_ubyte, cam_dims[1]*cam_dims[3]*3),
                                      frmGrab = Value(ctypes.c_byte, 0),
                                      camq = None,
                                      camq_p2read = None,
                                      frame_size = None
                                      )
            self.cam_dict[new_cam.serial] = new_cam
            
            self.cam_crop.add_crop(self.cam_cfg[new_cam.name]['crop'])
            if self.cam_cfg[name]['ismaster'] or is_unconnected:
                self.primary_cams.append(new_cam.serial)
            else: 
                self.secondary_cams.append(new_cam.serial)
        camCt = len(self.cam_dict)
        cam_names = [self.cam_dict[cam].name for cam in self.cam_dict]
        self.ctrl_panel.hardware_test(30*2, camCt, cam_names)
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        for ndx in range(self.cam_pointer, self.cam_pointer+2):
            serial = list(self.cam_dict)[ndx]
            self.im.append(self.axes[ndx].imshow(self.cam_dict[serial].frame))
            self.im[ndx].set_clim(0,255)
            self.cam_crop.update_crop(ndx, self.axes[ndx], self.cam_dict[serial].frame_dims)
        self.image_panel.update_names([self.cam_dict[list(self.cam_dict)[self.cam_pointer]].name, 
                                       self.cam_dict[list(self.cam_dict)[self.cam_pointer+1]].name]) 
        self.image_panel.draw()
    
    
    def initialize(self, event):
        self.serial.init_serial()
        self.initThreads()
        try: 
            self.updateSettings(event)
        except:
            logger.info('\nTrying to fix cameras. Please wait...\n')
            self.deinitThreads()
            self.camReset(event)
            self.initThreads()

            try:
                self.updateSettings(event)
            except:
                return False
        self.get_exposure(event)
        self.updateSettings(event)
        self.camaq.value = 1
        self.startAq()
        time.sleep(0.5)
        self.camaq.value = 0
        self.stopAq()
        
        for ndx, cam in enumerate(self.cam_dict):
            self.cam_dict[cam].frame = np.zeros(self.cam_dict[cam].shape, dtype='ubyte')
            self.cam_dict[cam].frameBuff[0:] = np.frombuffer(self.cam_dict[cam].array4feed.get_obj(), self.dtype, self.cam_dict[cam].size)
            dimensions = self.cam_crop.croproi[ndx] if self.crop else self.cam_dict[cam].frame_dims
            
            new_dims = FrameDims(x1 = dimensions[0],
                                 x2 = dimensions[0] + dimensions[1],
                                 y1 = dimensions[2],
                                 y2 = dimensions[2] + dimensions[3],
                                 h = dimensions[3],
                                 w = dimensions[1],
                                 dispSize = dimensions[3] * dimensions[1] * 3
                                 )            
            
            frame = self.cam_dict[cam].frameBuff[0:new_dims.dispSize].reshape([new_dims.h, new_dims.w,3])
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            for f in range(3):
                self.cam_dict[cam].frame[new_dims.y1: new_dims.y2, new_dims.x1: new_dims.x2,f] = frame[:,:,f]
            self.cam_dict[cam].frame_size = new_dims
        
        self.im[0].set_data(self.cam_dict[list(self.cam_dict)[self.cam_pointer]].frame)
        self.im[1].set_data(self.cam_dict[list(self.cam_dict)[self.cam_pointer+1]].frame)
        return True

    
    def deinitialize(self):
        self.serial.close()

        for ndx, im in enumerate(self.im):
            frame = np.zeros(self.cam_dict[list(self.cam_dict)[ndx]].shape, dtype='ubyte')
            im.set_data(frame)
            self.cam_crop.croprec[ndx].set_alpha(0)

        self.deinitThreads()
    
    
    def camReset(self,event):
        self.initThreads()
        self.camaq.value = 2
        self.startAq()
        time.sleep(3)
        self.stopAq()
        self.deinitThreads()
        logger.info('\n*** CAMERAS RESET ***\n')
        
    def live_start(self):
        self.camaq.value = 1
        self.startAq()
    
    def live_stop(self):
        self.stopAq()
        time.sleep(2)
        
    def vidPlayer(self, event):
        if self.camaq.value == 2:
            return
        self.participant_monitor.update_screen()
        for ndx, im in enumerate(self.cam_dict):
            if self.cam_dict[im].frmGrab.value == 1:
                self.cam_dict[im].frameBuff[0:] =  np.frombuffer(self.cam_dict[im].array4feed.get_obj(), 
                                                                 self.dtype, 
                                                                 self.cam_dict[im].size)
                dims = self.cam_dict[im].frame_size
                frame = self.cam_dict[im].frameBuff[0:dims.dispSize].reshape([dims.h, dims.w,3])
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                for f in range(3):
                    self.cam_dict[im].frame[dims.y1: dims.y2, dims.x1: dims.x2,f] = frame[:,:,f]
                self.cam_dict[im].frame_size = dims
                
                if ndx == self.cam_pointer:
                    self.im[0].set_data(self.cam_dict[im].frame)
                elif ndx == self.cam_pointer+1:
                    self.im[1].set_data(self.cam_dict[im].frame)
                self.cam_dict[im].frmGrab.value = 0
 
               
                if self.hardware_test:
                    self.cam_dict[im].cam_tests = np.roll(self.cam_dict[im].cam_tests, 1)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                    variance = laplacian.var()
                    self.cam_dict[im].cam_tests[0] = variance
                    
                    normalized_img = gray / 255.0
                    # Calculate RMS contrast (Standard Deviation)
                    rms = np.std(normalized_img)
                    self.cam_dict[im].contrast_tests = np.roll(self.cam_dict[im].contrast_tests, 1)
                    self.cam_dict[im].contrast_tests[0] = rms
        if self.hardware_test:
            if self.focus_test.GetValue():
                self.update_focus()
            elif self.contrast_test.GetValue():
                self.update_contrast()
        self.figure.canvas.draw()
        
    def update_focus(self, plot = True):
        if plot:
            cam_list = []
            for cam in self.cam_dict:
                cam_list.append(self.cam_dict[cam].cam_tests)
            self.ctrl_panel.plot_hardware(cam_list, 300)
        else:
            for cam in self.cam_dict:
                self.cam_dict[cam].cam_tests = np.full(shape=30*2, fill_value=np.nan)
                
                
    def update_contrast(self, plot = True):
        if plot:
            cam_list = []
            for cam in self.cam_dict:
                cam_list.append(self.cam_dict[cam].contrast_tests)
            self.ctrl_panel.plot_hardware(cam_list, 1)
        else:
            for cam in self.cam_dict:
                self.cam_dict[cam].cam_tests = np.full(shape=30*2, fill_value=np.nan)
                
                
    def start_recording(self, event, base_dir, sess_dir, path_base, count):
        totTime = 20 #int(self.secRec.GetValue())+int(self.minRec.GetValue())*60
        spaceneeded = 0
        freespace = shutil.disk_usage(base_dir)[2]
        for ndx, w in enumerate(self.cam_dict):
            recSize = self.aqW[ndx]*self.aqH[ndx]*3*self.cam_dict[w].actual_framerate*totTime
            spaceneeded+=recSize
        if spaceneeded > freespace:
            self.warning.update_error("space")
            self.warning.display()
        
        logger.info(f"Total estimated run time: {totTime}")
        for ndx, s in enumerate(self.cam_dict):
            camID = str(s)
            self.cam_dict[camID].camq.put('recordPrep')
            name_base = "%s_%s_trial%03d" % (path_base, self.cam_dict[camID].name, count)
            new_base = os.path.join(sess_dir,name_base)
            self.cam_dict[camID].camq.put(new_base)
            self.cam_dict[camID].camq_p2read.get()

        self.camaq.value = 1
        self.startAq()
    
    def stop_recording(self,event):
        self.shared.value = -1
        self.stopAq()
        time.sleep(2)

        
    def initThreads(self):
        self.camq = dict()
        self.camq_p2read = dict()
        self.cam = list()
        for ndx, camID in enumerate(self.cam_dict):
            self.cam_dict[camID].camq = Queue()
            self.cam_dict[camID].camq_p2read = Queue()
            self.cam.append(spin.multiCam_DLC_Cam(self.cam_dict[camID].camq, 
                                                  self.cam_dict[camID].camq_p2read,
                                                  camID, 
                                                  list(self.cam_dict),
                                                  self.cam_dict[camID].frame_dims, 
                                                  self.camaq,
                                                  self.frmaq, 
                                                  self.cam_dict[camID].array4feed,
                                                  self.cam_dict[camID].frmGrab, 
                                                  DOWNSAMPLE_VAL))

            self.cam[ndx].start()
        time.sleep(1)
        for cam in self.cam_dict:
            initialization = "InitS" if not self.cam_dict[cam].is_primary else "InitM"
            self.cam_dict[cam].camq.put(initialization)
            self.cam_dict[cam].camq_p2read.get()
            
            
    def deinitThreads(self):
        for n, camID in enumerate(self.cam_dict):
            self.cam_dict[camID].camq.put('Release')
            self.cam_dict[camID].camq_p2read.get()
            self.cam_dict[camID].camq.close()
            self.cam_dict[camID].camq_p2read.close()
            self.cam[n].terminate()
            
            
    def startAq(self):
        if self.serial.serSuccess:
            msg = f'S{self.session}x{self.trial}x'
            self.serial.write(msg)
            
        if self.camaq.value < 2:
            self.camaq.value = 1
            
        for cam in self.cam_dict:
            self.cam_dict[cam].camq.put('Start')
        for cam in self.primary_cams:
            self.cam_dict[cam].camq.put('TrigOff')
        
        
    def stopAq(self):
        if self.serial.serSuccess:
            msg = 'Xx'
            self.serial.ser.write(msg.encode())
        error_message = []
        video_errors = []
        self.camaq.value = 0
        threshold = 1
        for cam in self.secondary_cams:
            self.cam_dict[cam].camq.put('Stop')
            update = self.cam_dict[cam].camq_p2read.get()
            if update != "done":
                if int(update) > threshold:
                    error_message.append(f"{update}% of camera frames dropped for {cam}")
                self.cam_dict[cam].camq_p2read.get()
        for cam in self.primary_cams:
            self.cam_dict[cam].camq.put('Stop')
            update = self.cam_dict[cam].camq_p2read.get()
            if update != "done":
                if int(update) > threshold:
                    error_message.append(f"{update}% of camera frames dropped for {cam}")
                self.cam_dict[cam].camq_p2read.get()
        logger.warn(error_message)
        error = ""
        if video_errors:
            error = '\n' + '\n'.join(video_errors)
        if error_message:
            if error == "":
                error += "\n"
            error += '\n' + '\n'.join(error_message)
        if error != "":
            self.warning.update_error("frames", info=error)
            self.warning.display()


        
    def updateSettings(self, event):
        self.user_cfg = file_utils.read_config('userdata.yaml')
        self.aqW = list()
        self.aqH = list()
        self.recSet = list()
        for n, camID in enumerate(self.cam_dict):
                self.cam_dict[camID].camq.put('updateSettings')
                suc_test = self.cam_dict[camID].camq_p2read.get()
                if suc_test == -1:
                    raise ValueError("Cameras unresponsive")
                message = "crop" if self.crop else "full"
                self.cam_dict[camID].camq.put(message)
            
                # self.recSet.append(self.cam_dict[camID].camq_p2read.get())
                self.aqW.append(self.cam_dict[camID].camq_p2read.get())
                self.aqH.append(self.cam_dict[camID].camq_p2read.get())


    def get_exposure(self, event): 
        for n, camID in enumerate(self.cam_dict):
                self.cam_dict[camID].camq.put('setExposure')
        self.startAq()
        self.camaq.value = 1
        time.sleep(1)
        self.camaq.value = 0
        self.stopAq()
        for n, camID in enumerate(self.cam_dict):
            self.cam_dict[camID].camq.put('getExposure')
            self.cam_dict[camID].exposure = self.cam_dict[camID].camq_p2read.get()
            
        for n, camID in enumerate(self.cam_dict):
            self.cam_dict[camID].camq.put('setBalance')
        self.startAq()
        self.camaq.value = 1
        time.sleep(1)
        self.camaq.value = 0
        self.stopAq()
        primary_rate = self.framerate
        if len(self.primary_cams) <= 1:
            self.cam_dict[self.primary_cams[0]].camq.put('getBalance')
            rate = self.cam_dict[self.primary_cams[0]].camq_p2read.get()
            primary_rate = self.cam_dict[self.primary_cams[0]].actual_framerate = rate
        for n, camID in enumerate(self.cam_dict):
            if not self.cam_dict[camID].is_primary:
                self.cam_dict[camID].actual_framerate = primary_rate/int(self.cam_dict[camID].decrease_val)
                self.cam_dict[camID].camq.put('getBalance')
                
    def update_crop(self, value):
        self.crop = value
        
 
    def update_cameras_viewed(self, event):
        #switching which 2 cameras are seen
        if self.cam_pointer+2 >=  len(self.cam_dict):
            self.cam_pointer = 0
        else:
            self.cam_pointer+=2
            
        self.im[0].set_data(self.cam_dict[list(self.cam_dict)[self.cam_pointer]].frame)
        
        cam1 = self.cam_dict[list(self.cam_dict)[self.cam_pointer]].name
        
        if not (len(self.cam_dict) <= self.cam_pointer+1):
            cam2 = self.cam_dict[list(self.cam_dict)[self.cam_pointer+1]].name
            self.im[1].set_data(self.cam_dict[list(self.cam_dict)[self.cam_pointer+1]].frame)
        else:
            cam2 = ""
            self.im[1].set_data(np.zeros(self.cam_dict[list(self.cam_dict)[self.cam_pointer]].shape, dtype='ubyte')) 

        self.image_panel.update_names([cam1, cam2]) 

    def reset_variables(self):
        self.labjack_scan_rate = None
        self.camStrList = list()
        self.cam_settings = []
        self.secondary_cams = list()
        self.primary_cams = list()
        self.cam_pointer = 0
        self.im = list()
        self.exposure = []
        self.x1 = 0
        self.y1 = 0
        self.shared.value = 0
        self.camaq.value = 0
        self.frmaq.value = 0
        self.crop = True
        self.hardware_test = True