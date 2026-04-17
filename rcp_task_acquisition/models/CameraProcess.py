# -*- coding: utf-8 -*-
import time
from math import floor
from multiprocessing import Process
from queue import Empty
import numpy as np
import PySpin
import sys, linecache
import cv2

import rcp_task_acquisition.utils.file_utils as file_utils
from rcp_task_acquisition.utils.camera_utils import identify_dropped_frames
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/CameraProcess") 

        
class multiCam_DLC_Cam(Process):
    def __init__(self, camq, camq_p2read, camID,
                 idList,cpt, aq, frm, array4feed, frmGrab):
        super().__init__()
        self.camID = camID
        self.camq = camq
        self.camq_p2read = camq_p2read
        self.idList = idList
        self.cpt = cpt
        self.aq = aq
        self.frm = frm
        self.array4feed = array4feed
        self.frmGrab = frmGrab
        self.actual_exposure = None
        self.actual_frame_rate = None
        self.video_thread = None
        self.fps = None
        self.width = None
        self.height = None
        
        
    def run(self):
        record = False
        ismaster = False
        isunconnected = False
        record_frame_rate = 30
        exposure_max = 4000
        user_cfg = file_utils.read_config('userdata.yaml')["cameras"]
        test_num = 0
        camStrList = list()
        
        for s in user_cfg:
            if not user_cfg[s]["in_use"]:
                continue
            camStrList.append(s)
            if self.camID == str(user_cfg[s]['serial']):
                camStr = s
        logger.debug(camStr)
        # camCt = len(self.camStrList)

        
        current_exposure_time = int(user_cfg[camStr]['exposure'])
        frameSml = np.zeros([user_cfg[camStr]['crop'][3],user_cfg[camStr]['crop'][1]],'ubyte')
        aqW = self.cpt[3]
        aqH = self.cpt[1]
        frame = np.zeros([aqH,aqW,3],'ubyte')
        method = 'none'
        system = PySpin.System.GetInstance()
        
        logger.debug(f"{camStr} {system}")
        cam_list = system.GetCameras()
        logger.debug(f"{camStr} {cam_list}")
        cam = cam_list.GetBySerial(self.camID)
        processor = PySpin.ImageProcessor()
        processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
        while True:
            time.sleep(0.005)
            try:
                msg = self.camq.get(block=False)
                logger.debug(f"{camStr} msg: {msg}")
                try:
                    if msg == 'InitM':
                        ismaster = True
                        
                        logger.debug(f"{camStr} m here")
                        cam.Init()
                        self.create_primary(cam)
                        logger.debug(f'{camStr} m here')
                        self.camq_p2read.put('done')
                        logger.debug(f'{camStr} initialized as primary')
                    if msg == 'InitS':
                        logger.debug(f"{camStr} s here")
                        cam.Init()
                        self.create_secondary(cam)
                        logger.debug(f'{camStr} s here')
                        self.camq_p2read.put('done')
                        logger.debug(f'{camStr} initialized as secondary')
                    if msg == 'InitC':
                        cam.Init()
                        cam.LineSelector.SetValue(PySpin.LineSelector_Line2)
                        cam.V3_3Enable.SetValue(False)
                        cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                        cam.LineSource.SetValue(PySpin.LineSource_ExposureActive)
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                        cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
                        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_Off)
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                        isunconnected = True
                        self.camq_p2read.put('done')
                    elif msg == 'Release':
                        cam.DeInit()
                        del cam
                        for i in self.idList:
                            cam_list.RemoveBySerial(str(i))
                        cam_list.Clear()
                        system.ReleaseInstance() # Release instance
                        self.camq_p2read.put('done')
                    elif msg == 'recordPrep':
                        path_base = self.camq.get()
                        write_frame_rate = record_frame_rate
                        s_node_map = cam.GetTLStreamNodeMap()
                        handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
                        if not PySpin.IsAvailable(handling_mode) or not PySpin.IsWritable(handling_mode):
                            logger.warn('Unable to set Buffer Handling mode (node retrieval). Aborting...\n')
                            return
                        handling_mode_entry = handling_mode.GetEntryByName('OldestFirst')
                        handling_mode.SetIntValue(handling_mode_entry.GetValue())
                        logger.debug(path_base)
                        avi = PySpin.SpinVideo()
                        option = PySpin.AVIOption()
                        
                        option.frameRate = write_frame_rate
                        self.height = aqH
                        self.width = aqW
                        self.fps = round(write_frame_rate,2)
                        self.video_file = path_base+".mp4"
                        self.prepare_writers()
                        file_path = f'{path_base}_timestamps.txt'
                        f = open(file_path, 'w')
                        start_time = 0
                        capture_duration = 0
                        record = True
                        self.camq_p2read.put('done')
                    elif msg == 'Start':
                        cam.BeginAcquisition()
                        
                        if ismaster or isunconnected:
                            self.frm.value = 0
                            self.camq.get()
                            cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                        while self.aq.value > 0:
                            try:
                                image_result = cam.GetNextImage(100) #trying with timeout
                            except PySpin.SpinnakerException as e:
                                # when doing hardware test, pass value to parent 
                                # and alert that sync cable error
                                logger.error(f"timeout error: {e}")
                                # cam.EndAcquisition()
                                # cam.DeInit()
                                continue
                            image_result = processor.Convert(image_result, PySpin.PixelFormat_RGB8)
                            frame_results = image_result.GetNDArray()
                            if record:
                                frame_results_rgb = cv2.cvtColor(frame_results, cv2.COLOR_RGB2BGR)
                                test_num+=1
                                self.video_writer.write(frame_results_rgb)
                                if start_time == 0:
                                    start_time = image_result.GetTimeStamp()
                                else:
                                    time_test = image_result.GetTimeStamp()
                                    capture_duration = time_test- start_time
                                    start_time = time_test #image_result.GetTimeStamp()
                                    f.write("%s\n" % round(capture_duration))
                            
                            image_result.Release()     
                            if self.aq.value == 1:
                                # Live feed array
                                if self.frmGrab.value == 0:
                                    if np.shape(image_result.GetNDArray())[2] == 3:
                                        frame[:,:,:] = image_result.GetNDArray() #frame_results
                                        self.array4feed[0:aqH*aqW*3] = frame.flatten()
                                    self.frmGrab.value = 1
                            if ismaster:
                                self.frm.value+=1
                            
                        self.camq.get()
                        percentage_dropped = 0
                        if record:
                            f.close()
                            self.video_writer.release()
                            dropped_frame, total_frames, files_len = identify_dropped_frames(file_path, 
                                                                    int(user_cfg[camStr]['framerate']))
                            percentage_dropped = int(np.ceil((dropped_frame/total_frames)*100))
                            logger.debug(f"{self.camID}: total: {total_frames}, dropped: {dropped_frame}, len: {files_len}")
                            logger.debug(f"{dropped_frame} of camera frames dropped for {self.camID}")
                            logger.debug(f"{percentage_dropped}% of camera frames dropped for {self.camID}")

                            self.camq_p2read.put(percentage_dropped)
                            record = False
                            
                        cam.EndAcquisition()
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                        self.frmGrab.value = 0
                        if ismaster:
                            cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                            cam.LineSource.SetValue(PySpin.LineSource_FrameTriggerWait)
                            cam.LineInverter.SetValue(True)
                            cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                            cam.LineSource.SetValue(PySpin.LineSource_Counter0Active)
                        self.camq_p2read.put('done')
                    
                    elif msg == 'updateSettings':
                        nodemap = cam.GetNodeMap()
                        binsize = user_cfg[camStr]['bin']
                        
                        cam.BinningHorizontal.SetValue(int(binsize))
                        cam.BinningVertical.SetValue(int(binsize))
                        
                        # cam.IspEnable.SetValue(False)
                        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
                        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                            logger.warn('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
                            return False
                        # Retrieve entry node from enumeration node
                        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
                        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                                node_acquisition_mode_continuous):
                            logger.warn('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
                            return False
                        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
                        # Set integer value from entry node as new value of enumeration node
                        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
                        # Retrieve the enumeration node from the nodemap
                        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
                        if PySpin.IsAvailable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):
                            
                            # # Retrieve the desired entry node from the enumeration node
                            # node_pixel_format_mono8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono8'))
                            # if PySpin.IsAvailable(node_pixel_format_mono8) and PySpin.IsReadable(node_pixel_format_mono8):
                            #     # Retrieve the integer value from the entry node
                            #     pixel_format_mono8 = node_pixel_format_mono8.GetValue()
                            #     # Set integer as new value for enumeration node
                            #     node_pixel_format.SetIntValue(pixel_format_mono8)
                            # else:
                            #     logger.warn('Pixel format mono 8 not available...')
                                

                            node_pixel_format_BayerRG8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('BayerRG8'))
                            if PySpin.IsAvailable(node_pixel_format_BayerRG8) and PySpin.IsReadable(node_pixel_format_BayerRG8):
                                # Retrieve the integer value from the entry node
                                pixel_format_BayerRG8 = node_pixel_format_BayerRG8.GetValue()
                                # Set integer as new value for enumeration node
                                node_pixel_format.SetIntValue(pixel_format_BayerRG8)
                            else:
                                logger.debug('Pixel format BayerRG8 not available...')

                        else:
                            logger.warn('Pixel format not available...')
                            
                            
                        # Apply minimum to offset X
                        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
                        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                            node_offset_x.SetValue(node_offset_x.GetMin())
                        else:
                            logger.warn('Offset X not available...')
                        # Apply minimum to offset Y
                        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
                        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
                            node_offset_y.SetValue(node_offset_y.GetMin())
                        else:
                            logger.warn('Offset Y not available...')
                        # Set maximum width
                        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
                        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
                            width_to_set = node_width.GetMax()
                            node_width.SetValue(width_to_set)
                        else:
                            logger.warn('Width not available...')
                        # Set maximum height
                        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
                        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                            height_to_set = node_height.GetMax()
                            node_height.SetValue(height_to_set)
                        else:
                            logger.warn('Height not available...')
                        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
                        cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off)
                        
                        # cam.AdcBitDepth.SetValue(PySpin.AdcBitDepth_Bit8)
                        user_cfg = file_utils.read_config('userdata.yaml')["cameras"]
                        self.camq_p2read.put('done')
                        method = self.camq.get()
                        if method == 'crop':
                                
                            roi = self.cpt
                            
                            record_frame_rate = int(user_cfg[camStr]['framerate'])
                            # Set width
                            node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
                            width_max = node_width.GetMax()
                            width_to_set = np.floor(width_max/roi[3]*user_cfg[camStr]['crop'][1]/4)*4
                            if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
                                node_width.SetValue(int(width_to_set))
                            else:
                                logger.warn('Width not available...')
                            # Set height
                            node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
                            height_max = node_height.GetMax()
                            height_to_set = np.floor(height_max/roi[1]*user_cfg[camStr]['crop'][3]/4)*4
                            if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                                node_height.SetValue(int(height_to_set))
                            else:
                                logger.warn('Height not available...')
    
                            # Apply offset X
                            node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
                            offset_x = np.floor(width_max/roi[3]*user_cfg[camStr]['crop'][0]/4)*4
                            if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                                node_offset_x.SetValue(int(offset_x))
                            else:
                                logger.warn('Offset X not available...')
                            # Apply offset Y
                            node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
                            offset_y = np.floor(height_max/roi[1]*user_cfg[camStr]['crop'][2]/4)*4
                            if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
                                node_offset_y.SetValue(int(offset_y))
                            else:
                                logger.warn('Offset Y not available...')
                                
                            aqW = user_cfg[camStr]['crop'][1]
                            aqH = user_cfg[camStr]['crop'][3]
                        
                        else:
                            aqW = self.cpt[3]
                            aqH = self.cpt[1]
                            record_frame_rate = int(10)
                            
                        frame = np.zeros([aqH,aqW,3],'ubyte')
                        cam.AcquisitionFrameRateEnable.SetValue(True)
                        cam.Gain.SetValue(user_cfg[camStr]['gain'])
                        # Ensure desired frame rate does not exceed the maximum
                        max_frmrate = cam.AcquisitionFrameRate.GetMax()
                        frmrate_time_to_set = min(max_frmrate, record_frame_rate)
                        cam.AcquisitionFrameRate.SetValue(frmrate_time_to_set)
                        exposure_time_to_set = cam.ExposureTime.GetValue()
                        logger.info(f"exposure: {exposure_time_to_set}")
                        record_frame_rate = cam.AcquisitionFrameRate.GetValue()
                        exposure_time_request = int(user_cfg[camStr]['exposure'])
                        
                        cam.AcquisitionFrameRateEnable.SetValue(False)
                        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                            logger.warn('Unable to disable automatic exposure. Aborting...')
                            continue
                        # cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
                        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
                            logger.warn('Unable to set exposure time. Aborting...')
                            continue
                        # # Ensure desired exposure time does not exceed the maximum
                        exposure_time_to_set = floor(1/record_frame_rate*1000*1000)
                        if exposure_time_request <= exposure_time_to_set:
                            exposure_time_to_set = exposure_time_request
                        max_exposure = cam.ExposureTime.GetMax()
                        current_exposure_time = min(max_exposure, exposure_time_to_set)
                        cam.ExposureTime.SetValue(current_exposure_time)

                        cam.AcquisitionFrameRateEnable.SetValue(True)
                        cam.Gain.SetValue(user_cfg[camStr]['gain'])
                        cam.Gamma.SetValue(user_cfg[camStr]['gamma'])
                        # Ensure desired frame rate does not exceed the maximum
                        max_frmrate = cam.AcquisitionFrameRate.GetMax()
                        cam.AcquisitionFrameRate.SetValue(frmrate_time_to_set)
                        exposure_time_to_set = cam.ExposureTime.GetValue()
                        record_frame_rate = cam.AcquisitionFrameRate.GetValue()

                        # max_exposure = cam.ExposureTime.GetMax()
                        # self.camq_p2read.put(exposure_time_to_set)
                        logger.info(f"frame rate {user_cfg[camStr]['nickname']}: {str(round(record_frame_rate))}")
                        # self.camq_p2read.put(max_exposure)
                        self.camq_p2read.put(record_frame_rate)
                        self.camq_p2read.put(node_width.GetValue())
                        self.camq_p2read.put(node_height.GetValue())
                    
                    elif msg == "setExposure":
                        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
                    
                    elif msg == 'getExposure':
                        
                        logger.info(f"Current exposure: {current_exposure_time}" )
                        current_exposure_time = cam.ExposureTime.GetValue()*.9
                        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                        current_exposure_time = min(current_exposure_time,exposure_max)
                        cam.ExposureTime.SetValue(current_exposure_time)
                        logger.info(f"Auto-exposure result {camStr}: {current_exposure_time}")
                        logger.debug(f"exposure: {cam.ExposureTime.GetValue()}")
                        self.camq_p2read.put(cam.ExposureTime.GetValue())
                    elif msg == "setBalance":
                        cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Continuous)
                    
                    elif msg == 'getBalance':
                        
                        cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off)
                        cam.Gain.SetValue(user_cfg[camStr]['gain'])
                        cam.Gamma.SetValue(user_cfg[camStr]['gamma'])
                        cam.AcquisitionFrameRate.SetValue(frmrate_time_to_set)
                        record_frame_rate = cam.AcquisitionFrameRate.GetValue()
                        logger.debug(f"fps: {record_frame_rate}")
                        
                        self.camq_p2read.put(record_frame_rate)
                        logger.info(f"Auto-exposure frame rate {camStr}: {record_frame_rate}")
                        
                        

                except PySpin.SpinnakerException:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    linecache.checkcache(filename)
                    line = linecache.getline(filename, lineno, f.f_globals)
                    logger.exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
                    logger.exception(self.camID + ' : ' + camStr)
                    if msg == 'updateSettings':
                        self.camq_p2read.put(-1)
                        self.camq_p2read.put(30)
                        self.camq_p2read.put(30)
                    else:
                        self.camq_p2read.put('done')
            
            except Empty:
                pass
        
    
    def create_primary(self, cam):
        # logger.debug(f'{camStr} m here')
        cam.CounterSelector.SetValue(PySpin.CounterSelector_Counter0)
        cam.CounterEventSource.SetValue(PySpin.CounterEventSource_ExposureStart)
        cam.CounterEventActivation.SetValue(PySpin.CounterEventActivation_RisingEdge)
        cam.CounterTriggerSource.SetValue(PySpin.CounterTriggerSource_ExposureStart)
        cam.CounterTriggerActivation.SetValue(PySpin.CounterTriggerActivation_RisingEdge)
        cam.LineSelector.SetValue(PySpin.LineSelector_Line2)
        cam.V3_3Enable.SetValue(True)
        cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
        cam.LineSource.SetValue(PySpin.LineSource_Counter0Active)
        cam.LineInverter.SetValue(False)
        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_Off)
        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
    
    def create_secondary(self, cam):
        # logger.debug(f'{camStr} s here')
        cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
        cam.TriggerActivation.SetValue(PySpin.TriggerActivation_AnyEdge)
        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
    
    def prepare_writers(self):
        video_file = self.video_file
        self.video_writer = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc('d', 'i', 'v', 'x'), self.fps, (self.width, self.height))