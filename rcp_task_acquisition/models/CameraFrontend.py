# -*- coding: utf-8 -*-
import datetime
import os
import time
import numpy as np
import shutil
import cv2
import ctypes
from multiprocessing import Queue, Value, Array

import rcp_task_acquisition.models.CameraProcess as spin
import rcp_task_acquisition.utils.file_utils as file_utils
from rcp_task_acquisition.models.Crop import Crop
from rcp_task_acquisition.models.Warnings import Warning
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/CameraFrontend") 



class Camera():
    def __init__(self, serial, panel, image_panel, contrast_test, focus_test):
        self.serial = serial
        self.frmDims = [0,540,0,720]
        self.shared = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.reset_variables()
        self.dtype = 'uint8'
        self.size = self.frmDims[1]*self.frmDims[3]*3
        self.shape = [self.frmDims[1], self.frmDims[3],3] 
        self.cam_crop = Crop()
        self.ctrl_panel = panel
        self.image_panel = image_panel
        self.contrast_test = contrast_test
        self.focus_test= focus_test
        self.warning = Warning()


    def setup(self, config, is_unconnected):
        self.cam_cfg = config
        if is_unconnected:
            self.unconnected = [str(self.cam_cfg[s]['serial']) for s in self.camStrList]
        else:
            for s in self.cam_cfg:
                if not self.cam_cfg[s]["in_use"]:
                    continue
                if not self.cam_cfg[s]['ismaster']:
                    self.slist.append(str(self.cam_cfg[s]['serial']))
                else:
                    self.master_list.append(str(self.cam_cfg[s]['serial']))
                self.camStrList.append(s)

        camCt = len(self.camStrList)
        for cam in self.camStrList:
            self.cam_tests.append(np.full(shape=30*2, fill_value=np.nan))
            self.contrast_tests.append(np.full(shape=30*2, fill_value=np.nan))
        
        self.ctrl_panel.hardware_test(30*2, camCt, self.camStrList)
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        frame = np.zeros(self.shape, dtype='ubyte')
        frameBuff = np.zeros(self.size, dtype='ubyte')
        for ndx, s in enumerate(self.camStrList):
            self.camIdList.append(str(self.cam_cfg[s]['serial']))
            self.cam_crop.add_crop(self.cam_cfg[s]['crop'])
            self.array4feed.append(Array(ctypes.c_ubyte, self.size))
            self.frmGrab.append(Value(ctypes.c_byte, 0))
            self.frame.append(frame)
            self.frameBuff.append(frameBuff)
        
        for ndx in range(self.cam_pointer, self.cam_pointer+2):
            self.im.append(self.axes[ndx].imshow(self.frame[ndx]))
            self.im[ndx].set_clim(0,255)
            self.cam_crop.update_crop(ndx, self.axes[ndx], self.frmDims)
        self.image_panel.update_names([self.camStrList[self.cam_pointer], self.camStrList[self.cam_pointer+1]])
        self.image_panel.draw()
    
    
    def initialize(self, event):
        self.serial.init_serial()
        # print('before init')
        self.initThreads()
        # print('after init')
        try: 
            self.updateSettings(event)
        except:
            #add wrning?
            logger.info('\nTrying to fix cameras. Please wait...\n')
            self.deinitThreads()
            self.camReset(event)
            self.initThreads()

            try:
                self.updateSettings(event)
            except:
                return False
        self.get_exposure(event)
        self.camaq.value = 1
        self.startAq()
        time.sleep(0.5)
        self.camaq.value = 0
        self.stopAq()
        self.x1 = list()
        self.x2 = list()
        self.y1 = list()
        self.y2 = list()
        self.h = list()
        self.w = list()
        self.dispSize = list()
        for ndx, im in enumerate(self.frame):
            self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
            self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
            if self.crop:
                self.h.append(self.cam_crop.croproi[ndx][3])
                self.w.append(self.cam_crop.croproi[ndx][1])
                self.y1.append(self.cam_crop.croproi[ndx][2])
                self.x1.append(self.cam_crop.croproi[ndx][0])
                # self.set_crop.Enable(False)
            else:
                self.h.append(self.frmDims[1])
                self.w.append(self.frmDims[3])
                self.y1.append(self.frmDims[0])
                self.x1.append(self.frmDims[2])
                # self.set_crop.Enable(True)

            self.dispSize.append(self.h[ndx]*self.w[ndx]*3)
            self.y2.append(self.y1[ndx]+self.h[ndx])
            self.x2.append(self.x1[ndx]+self.w[ndx])
            
            frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx],3])
            for f in range(3):
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx],f] = frame[:,:,f]

            self.im[0].set_data(self.frame[self.cam_pointer])
            self.im[1].set_data(self.frame[self.cam_pointer+1])
                
            self.cam_crop.croprec[0].set_alpha(0.6)
            self.cam_crop.croprec[1].set_alpha(0.6)
        return True

    
    def deinitialize(self):
        self.serial.close()
        for ndx, im in enumerate(self.im):
            self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
            im.set_data(self.frame[ndx])
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
        for ndx, im in enumerate(self.frame):
            if self.frmGrab[ndx].value == 1:
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx], 3])
                for f in range(3):
                    self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx],f] = frame[:,:,f]
                if ndx == self.cam_pointer:
                    self.im[0].set_data(self.frame[ndx])
                elif ndx == self.cam_pointer+1:
                    self.im[1].set_data(self.frame[ndx])
                self.frmGrab[ndx].value = 0
               
                if self.hardware_test:
                    self.cam_tests[ndx] = np.roll(self.cam_tests[ndx], 1)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                    variance = laplacian.var()
                    
                    self.cam_tests[ndx][0] = variance
                    
                    normalized_img = gray / 255.0
                    # Calculate RMS contrast (Standard Deviation)
                    rms = np.std(normalized_img)
                    self.contrast_tests[ndx] = np.roll(self.contrast_tests[ndx], 1)
                    self.contrast_tests[ndx][0] = rms
        if self.hardware_test:
            if self.focus_test.GetValue():
                self.ctrl_panel.plot_hardware(self.cam_tests, 300),
            elif self.contrast_test.GetValue():
                self.ctrl_panel.plot_hardware(self.contrast_tests, 1)
        self.figure.canvas.draw()
        
        
    def start_recording(self, event, base_dir, sess_dir, unit_ref, sess_string, count):

        totTime = 20 #int(self.secRec.GetValue())+int(self.minRec.GetValue())*60
        spaceneeded = 0
        freespace = shutil.disk_usage(base_dir)[2]
        for ndx, w in enumerate(self.aqW):
            recSize = w*self.aqH[ndx]*3*self.recSet[ndx]*totTime
            spaceneeded+=recSize
        if spaceneeded > freespace:
            self.warning.update_error("space")
            self.warning.display()
        
        logger.info(f"Total estimated run time: {totTime}")
        for ndx, s in enumerate(self.camStrList):
            camID = str(self.cam_cfg[s]['serial'])
            self.camq[camID].put('recordPrep')
            date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
            name_base = f"{date_string}_{unit_ref}_{sess_string}_{self.cam_cfg[s]['nickname']}_trial{count}" #% (date_string, self.user_cfg['unitRef'], self.sess_string, self.cam_cfg[s]['nickname'])
            path_base = os.path.join(sess_dir,name_base)
            self.camq[camID].put(path_base)
            self.camq_p2read[camID].get()

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
        for ndx, camID in enumerate(self.camIdList):
            self.camq[camID] = Queue()
            self.camq_p2read[camID] = Queue()
            self.cam.append(spin.multiCam_DLC_Cam(self.camq[camID], self.camq_p2read[camID],
                                               camID, self.camIdList,
                                               self.frmDims, self.camaq,
                                               self.frmaq, self.array4feed[ndx], self.frmGrab[ndx]))

            self.cam[ndx].start()
        time.sleep(1)
        for cam in self.unconnected:
            self.camq[cam].put('InitC')
            self.camq_p2read[cam].get()
        
        for cam in self.master_list:
            logger.debug(f"master_list {cam}")
            self.camq[cam].put('InitM')
            self.camq_p2read[cam].get()

        for s in self.slist:
            self.camq[s].put('InitS')
            self.camq_p2read[s].get()
            
            
    def deinitThreads(self):
        for n, camID in enumerate(self.camIdList):
            self.camq[camID].put('Release')
            self.camq_p2read[camID].get()
            self.camq[camID].close()
            self.camq_p2read[camID].close()
            self.cam[n].terminate()
            
            
    def startAq(self):
        if self.serial.serSuccess:
            msg = 'Sx'
            self.serial.write(msg)
        if self.camaq.value < 2:
            self.camaq.value = 1
        for cam in self.unconnected:
            self.camq[cam].put('Start')
        for cam in self.master_list:
            self.camq[cam].put('Start')
        for s in self.slist:
            self.camq[s].put('Start')
        for cam in self.master_list:
            self.camq[cam].put('TrigOff')
        for cam in self.unconnected:
            self.camq[cam].put('TrigOff')
        
        
    def stopAq(self):
        if self.serial.serSuccess:
            msg = 'Xx'
            self.serial.ser.write(msg.encode())
        error_message = []
        video_errors = []
        self.camaq.value = 0
        threshold = 10
        for s in self.unconnected:
            logger.debug(f" unconnected: {s}")
            self.camq[s].put('Stop')
            update = self.camq_p2read[s].get()
            if update == "video":
                video_errors.append(self.camq_p2read[s].get())
                update = self.camq_p2read[s].get()
            if update != "done":
                if int(update) > threshold:
                    error_message.append(f"{update}% of camera frames dropped for {s}")
                self.camq_p2read[s].get()
        for s in self.slist:
            self.camq[s].put('Stop')
            update = self.camq_p2read[s].get()
            if update == "video":
                errors = self.camq_p2read[s].get()
                video_errors.append(errors)
                update = self.camq_p2read[s].get()
            if update != "done":
                if int(update) > threshold:
                    error_message.append(f"{update}% of camera frames dropped for {s}")
                self.camq_p2read[s].get()
        for cam in self.master_list:
            self.camq[cam].put('Stop')
            update = self.camq_p2read[cam].get()
            if update == "video":
                errors = self.camq_p2read[cam].get()
                video_errors.append(errors)
                update = self.camq_p2read[cam].get()
            if update != "done":
                if int(update) > threshold:
                    error_message.append(f"{update}% of camera frames dropped for {cam}")
                self.camq_p2read[cam].get()
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
        for n, camID in enumerate(self.camIdList):
                self.camq[camID].put('updateSettings')
                suc_test = self.camq_p2read[camID].get()
                if suc_test == -1:
                    raise ValueError("Cameras unresponsive")
                if self.crop:
                    self.camq[camID].put('crop')
                else:
                    self.camq[camID].put('full')
            
                self.recSet.append(self.camq_p2read[camID].get())
                self.aqW.append(self.camq_p2read[camID].get())
                self.aqH.append(self.camq_p2read[camID].get())


    def get_exposure(self, event): 
        for n, camID in enumerate(self.camIdList):
                self.camq[camID].put('setExposure')
        self.startAq()
        self.camaq.value = 1
        time.sleep(1)
        self.camaq.value = 0
        self.stopAq()
        for n, camID in enumerate(self.camIdList):
            self.camq[camID].put('getExposure')
            actual_exposure = self.camq_p2read[camID].get()
            self.exposure.append(actual_exposure)
            
        for n, camID in enumerate(self.camIdList):
            self.camq[camID].put('setBalance')
        self.startAq()
        self.camaq.value = 1
        time.sleep(1)
        self.camaq.value = 0
        self.stopAq()
        for n, camID in enumerate(self.camIdList):
            self.camq[camID].put('getBalance')

            actual_rate = self.camq_p2read[camID].get()
            self.rate.append(actual_rate)

            
    def update_crop(self, value):
        self.crop = value
        
        
    def update_cameras_viewed(self, event):
        #switching which 2 cameras are seen
        if self.cam_pointer+2 >=  len(self.camStrList):
            self.cam_pointer = 0
        else:
            self.cam_pointer+=2
        self.im[0].set_data(self.frame[self.cam_pointer])
        if len(self.camStrList) <= self.cam_pointer+1:
            self.im[1].set_data(np.zeros(self.shape, dtype='ubyte')) 
            self.image_panel.update_names([self.camStrList[self.cam_pointer], " "])
        else:
            self.im[1].set_data(self.frame[self.cam_pointer+1])
            self.image_panel.update_names([self.camStrList[self.cam_pointer], self.camStrList[self.cam_pointer+1]])


    def reset_variables(self):
        self.labjack_scan_rate = None
        self.camStrList = list()
        self.slist = list()
        self.master_list = list()
        self.unconnected = list()
        self.cam_pointer = 0
        self.im = list()
        self.camIdList = list()
        self.frame = list()
        self.frameBuff = list()
        self.frmGrab = list()
        self.array4feed = list()
        self.rate = []
        self.exposure = []
        self.cam_tests = []
        self.contrast_tests = []
        self.x1 = 0
        self.y1 = 0
        self.shared.value = 0
        self.camaq.value = 0
        self.frmaq.value = 0
        self.array4feed = list()
        self.crop = True
        self.hardware_test = True
        
        
        