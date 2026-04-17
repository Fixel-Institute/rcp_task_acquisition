"""
file_utils toolbox
https://github.com/wryanw/file_utils
W Williamson, wallace.williamson@ucdenver.edu

"""
import os
import sys
import time, datetime
from multiprocessing import Value, Queue
import wx
import wx.lib.dialogs
import numpy as np
import ctypes
import shutil

import rcp_task_acquisition.utils.file_utils as file_utils
from rcp_task_acquisition.utils.file_utils import read_config
from rcp_task_acquisition.models.StimulusThread import StimulusThread
from rcp_task_acquisition.models.LabjackFrontend import LabjackFrontend
from rcp_task_acquisition.models.Crop import Crop
from rcp_task_acquisition.panels.GraphPanel import GraphPanel
from rcp_task_acquisition.models.Warnings import Warning
from rcp_task_acquisition.panels.MetadataPanel import MetadataPanel
from rcp_task_acquisition.utils.constants import RAW_DATA_DIR, PLOT_LENGTH
from rcp_task_acquisition.panels.ControlsPanel import ControlsPanel
from rcp_task_acquisition.panels.ImagePanel import ImagePanel
from rcp_task_acquisition.models.SerialDevice import SerialDevice
from rcp_task_acquisition.models.CameraFrontend import Camera
from rcp_task_acquisition.utils.task_acquisistion_version import __version__
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/MainFrame") 


class MainFrame(wx.Frame):
    """Contains the main GUI and button boxes"""
    def __init__(self, parent=None):
        self.task_cfg = None
        self.task = None
        self.cam_cfg = {}
        self.trial_button = None
        self.button_pressed = Value(ctypes.c_bool, False)
        self.recording = False
        self.press_count = Value(ctypes.c_int, 0)
        self.stimulus_panel = Value(ctypes.c_bool, False)
        self.hardware_list = [[], [], []]
        self.count = 0
        self.results_list = []
        self.serial_device = SerialDevice()
        self.cam_crop = Crop()
        #setting up screen for stimulus thread
        self.user_cfg = file_utils.read_config('userdata.yaml')
        screen_settings = self.user_cfg["screen_settings"]
        
        # Settting the GUI size and panels design
        displays = (wx.Display(i) for i in range(wx.Display.GetCount())) # Gets the number of displays
        screenSizes = [display.GetGeometry().GetSize() for display in displays] # Gets the size of each display
        logger.debug(f"screenSizes: {screenSizes}")
        index = 0 # For display 1.
        screenW = screenSizes[index][0]
        screenH = screenSizes[index][1]
        
        self.gui_size = (int(screenW*0.9), int(screenW*0.45))
        # self.gui_size = (screenW-90, screenH-55)
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'Task Master Aquisition',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, 
                            style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

        # self.Maximize(True)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("")
        self.SetSizeHints(wx.Size(self.gui_size)) #  This sets the minimum size of the GUI. It can scale now!
        
        # Spliting the frame into top and bottom panels. Bottom panels contains the widgets. The top panel is for showing images and plotting!
        topSplitter = wx.SplitterWindow(self)
        vSplitter = wx.SplitterWindow(topSplitter)
        self.image_panel = ImagePanel(vSplitter)
        self.image_panel.updateImage(self.gui_size)
        self.ctrl_panel = GraphPanel(vSplitter, self.gui_size)
        self.widget_panel = ControlsPanel(topSplitter, self.ctrl_panel)

        vSplitter.SplitHorizontally(self.image_panel, self.ctrl_panel, sashPosition=int(self.gui_size[1]*0.6))
        topSplitter.SplitVertically(vSplitter, self.widget_panel, sashPosition=int(self.gui_size[0]*0.78))

        topSplitter.SetSashGravity(1)
        vSplitter.SetSashGravity(1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)
    
        # Add Buttons to the WidgetPanel and bind them to their respective functions.
        (self.init,self.reset,self.update_settings,self.play,self.rec,
        self.exposure_button,self.set_crop,self.crop, self.minRec,self.secRec) = self.widget_panel.get_cam_handles()

        (self.camera_toggle, self.hardware_button, 
         self.task_button,  self.quit, self.tens_button) = self.widget_panel.get_task_handles()
        (self.contrast_test, self.focus_test, self.hardware_test_panel) = self.widget_panel.get_hardware_handles()
        self.focus_test.Bind(wx.EVT_TOGGLEBUTTON, self.set_focus)
        self.contrast_test.Bind(wx.EVT_TOGGLEBUTTON, self.set_contrast)
        self.cams = Camera(self.serial_device, self.ctrl_panel, self.image_panel, self.contrast_test, self.focus_test)
        
        self.init.Bind(wx.EVT_TOGGLEBUTTON, self.initCams)
        self.update_settings.Bind(wx.EVT_BUTTON, self.cams.updateSettings)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.liveFeed)
        self.hardware_button.Bind(wx.EVT_TOGGLEBUTTON, self.disable_gui)
        self.rec.Bind(wx.EVT_TOGGLEBUTTON, self.recordCam)
        self.exposure_button.Bind(wx.EVT_BUTTON, self.cams.get_exposure)
        self.task_button.Bind(wx.EVT_TOGGLEBUTTON, self.disable_gui)
        self.tens_button.Bind(wx.EVT_BUTTON, self.tens_pulse)
        self.cam_test = Value(ctypes.c_bool, False)
        self.hardware_test = False
        self.liveTimer = wx.Timer(self, wx.ID_ANY)
        
        #labjack setup
        self.ctrl_panel.create_plot(PLOT_LENGTH)
        self.labjack_stream_button = self.ctrl_panel.get_graph_button()
        self.labjack_choices = self.ctrl_panel.get_graph_choices()
        
        self.labjack_timer = wx.Timer(self, wx.ID_ANY)
        self.lj = LabjackFrontend(PLOT_LENGTH, 
                                  self.ctrl_panel, 
                                  self.labjack_timer, 
                                  self.hardware_list,
                                  self.button_pressed,
                                  self.press_count,
                                  self.cam_test)
        
        self.Bind(wx.EVT_TIMER, self.lj.labjack_event, self.labjack_timer)
        self.labjack_stream_button.Bind(wx.EVT_TOGGLEBUTTON, self.disable_gui)
        
        #set up cam things
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        self.x1 = 0
        self.y1 = 0
        self.frmDims = [0,540,0,720]
        self.shared = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        
        self.dtype = 'uint8'
        self.size = self.frmDims[1]*self.frmDims[3]*3
        self.shape = [self.frmDims[1], self.frmDims[3],3] 
        self.array4feed = list()
        
        self.canvas.mpl_connect('button_press_event', self.onClick)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
        self.exit_stimulus = False
        self.Bind(wx.EVT_CHECKBOX, self.update_crop)
        self.warning = Warning()
        #check the display is correct
        #check the correct monitors are displayed
        if wx.Display.GetCount() < 2:
            self.warning.update_error("display")
            self.warning.display()
            sys.exit()

        self.camera_toggle.Bind(wx.EVT_BUTTON, self.cams.update_cameras_viewed)
        #set up stimulus thread
        '''
        0-> no video playing
        1-> video playing
        2-> video paused
        3-> video playing from pause
        4-> stop video fully
        5-> video finished run
        '''
        self.video_status = Value(ctypes.c_int, 0)
        self.threads = []
        self.msgq =  Queue()
        self.finish = Value(ctypes.c_byte, 0)
        self.resultsq = Queue()
        
        self.thread = StimulusThread( self.msgq, 
                                     self.finish, 
                                     self.shared, 
                                     self.frmaq,  
                                     screen_settings, 
                                     self.task, 
                                     self.button_pressed,
                                     self.press_count,
                                     self.video_status,
                                     self.resultsq)
        self.startingSession = False
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_intertrial, self.rest_timer)
        self.Bind(wx.EVT_TIMER, self.cams.vidPlayer, self.liveTimer)
        self.thread.start()
        self.task_active = False
        self.disable_timer = wx.Timer(self, wx.ID_ANY)
        
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def on_resize(self, event):
        wx.CallAfter(self.image_panel.reset_sizing)
        event.Skip() 
        # pass
    
    def run_task(self, event):
        self.Enable()
        if self.task_button.GetValue():
            self.task_active = True
            self.trial_dict = {}
            self.start_time= str(f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}Z') 
            self.count = 0
            self.finish.value = 0
            self.msgq.put("init_stimulus")
            self.create_file()
            is_success = self.lj.start_labjack()
            if not is_success:
                self.task_button.SetValue(False)
                return
            
            self.labjack_stream_button.SetValue(True)
            self.labjack_stream_button.Enable(False)
            self.labjack_stream_button.SetLabel("Stop Labjack")
            self.date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
            lj_path = os.path.join(self.sess_dir, f"{self.date_string}_{self.user_cfg['unitRef']}_{self.sess_string}_labjack.txt")
            msg = f"P{self.date_string}_{self.user_cfg['unitRef']}_{self.sess_string}x"
            self.lj.add_csv(lj_path, self.serial_device, msg)
            self.startingSession = True
            self.task_button.SetLabel("End Task")
            # self.hardware_button.Enable(False)
            if self.task == "vowel_space":
                self.msgq.put("vowel_space")
                trial_info = self.resultsq.get()
                trial, syllable, finish = trial_info.split(",")
                trial = int(trial)
                finish = str(finish) == "True"
                self.trial_panel.repeat = True
                self.trial_panel.update_trial(trial, syllable)
            self.trial_panel.start_new_trial()
            self.trial_panel.show()
        else:
            self.task_active = False
            self.serial_device.write("A")
            time.sleep(3)
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
            
            self.finish.value = 0
            self.labjack_stream_button.Enable(True)
            if self.labjack_stream_button.GetValue():
                self.labjack_stream_button.SetValue(False)
                self.labjack_stream_button.SetLabel("Stream Labjack")
            self.labjack_stream_button.Enable(True)
            self.end_time= str(f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}Z') 
            self.add_metadata()
            self.msgq.put("reset_task")
            self.labjack_timer.Start(200)
            # self.trial_panel.start_new_trial()

    
    def trial_event(self, event):
        if self.trial_button.GetValue():
            time.sleep(1)
            self.count +=1
            self.rest_timer.Start(1000)
            self.finish.value = 0
            try:
                self.msgq.put("update_data")
                
                data = str(self.trial_panel.get_result())
                self.msgq.put(data)
            except:
                self.results_list.append(self.trial_panel.get_result())
            # if self.task == "vowel_space":
            #     self.msgq.put("vowel_space")
            #     trial_info = self.resultsq.get()
            #     trial, syllable, finish = trial_info.split(",")
            #     trial = int(trial)
            #     finish = str(finish) == "True"
            #     self.trial_panel.update_trial(trial, syllable)
            #     if finish:
            #        self.trial_button.Enable(True) 
            #     return
            if self.task== "verbal_fluency" and self.trial_panel.first:
                self.count =0
                self.trial_button.SetLabel("Start Trial")
                self.trial_panel.switch_panel()
                data = str(self.trial_panel.get_trials())
                self.msgq.put("update_data")
                self.msgq.put(data)
                self.results_list.append(self.trial_panel.get_result())
                return
                   
            self.trial_panel.run_trial(self.count)
            self.trial_button.SetLabel("Stop Trial")
            self.cams.start_recording(event, self.base_dir, self.sess_dir, self.user_cfg['unitRef'], self.sess_string, self.count)
            self.liveTimer.Start(150)
            self.msgq.put("run_stimulus")

        else:
            self.rest_timer.Stop()
            self.finish.value = 2
            if self.task == "sara":
                self.trial_panel.show_scoring()
            elif self.task == "verbal_fluency":
                self.trial_panel.update_values()
            elif self.task == "vowel_space":
                self.trial_panel.repeat_trial.Enable(True)
                self.trial_button.SetLabel("Repeat Trial")
                self.trial_panel.repeat_trial.SetValue(False)
                self.cams.stop_recording(event)
                self.liveTimer.Stop()
                # self.msgq.put("update_data")
                self.trial_panel.next_button.Enable(True)
                # self.msgq.put(self.trial_panel.repeat)
                return
            # self.msgq.put("end_stimulus")
            self.cams.stop_recording(event)
            self.trial_button.SetLabel("Begin Trial")
            self.trial_panel.reset(self.count)
            self.trial_panel.end_trial()
            self.liveTimer.Stop()
    
    def next_trial(self, event):  
        logger.debug("UPDATING DATA")
        self.msgq.put("update_data")
        
        data = str(self.trial_panel.get_result())
        self.msgq.put("False")
        self.msgq.put("vowel_space")
        trial_info = self.resultsq.get()
        trial, syllable, finish = trial_info.split(",")
        self.trial_button.SetLabel("Begin Trial")
        trial = int(trial)
        finish = str(finish) == "True"
        self.trial_panel.update_trial(trial, syllable)
        if finish:
           self.trial_panel.is_finish()

        
    def repeat_event(self, event):
        self.trial_panel.repeat_event()
        self.trial_event(event)
        

    def update_intertrial(self, event):
        if self.video_status.value == 5:
            self.trial_panel.stop_video()
            self.video_status.value = 0
        elif (self.finish.value == 1 and 
        (self.task != "naturalistic_speech" and self.task != "vowel_space")):
            logger.debug("in intertrial")
            self.cams.stop_recording(event)
            self.trial_panel.reset(self.count)
            self.trial_panel.end_trial()
            self.stimulus_panel.value = False
            self.finish.value = 0
            self.trial_panel.update_values()
            self.trial_button.SetLabel("Start Trial")


    def play_instructions(self, event):
        if event.GetEventObject().GetValue():
            if type(self.trial_panel.get_instructions()) is str:
                result = ""
            else:
                result = self.trial_panel.get_instruction(self.count)
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


    def set_focus(self, event):
        if self.focus_test.GetValue():
            self.contrast_test.Enable(False)
            self.cam_test.value = True
            self.ctrl_panel.plot_hardware(self.cams.cam_tests, 300)
            self.ctrl_panel.setup_test_legend()
        else:
            self.ctrl_panel.remove_hardware()
            self.contrast_test.Enable(True)
            for cam_index in range(len(self.cams.cam_tests)):
                self.cams.cam_tests[cam_index] = np.full(shape=30*2, fill_value=np.nan)
            self.cam_test.value = False
 
    
    def set_contrast(self, event):
        if self.contrast_test.GetValue():
            self.focus_test.Enable(False)
            self.cam_test.value = True
            self.ctrl_panel.setup_test_legend()
            self.ctrl_panel.plot_hardware(self.cams.contrast_tests, 1)
        else:
            self.ctrl_panel.remove_hardware()
            self.focus_test.Enable(True)
            for cam_index in range(len(self.cams.contrast_tests)):
                self.cams.contrast_tests[cam_index] = np.full(shape=30*2, fill_value=np.nan)
            self.cam_test.value = False
        
        
    def liveFeed(self, event):
        clicked_button = event.GetEventObject()
        button_label = clicked_button.GetLabel()
        if button_label == "Abort":
            self.rec.SetValue(False)
            self.recordCam(event)
            if wx.MessageBox("Are you sure?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                shutil.rmtree(self.sess_dir)
                time.sleep(5)
            self.play.SetValue(False)
            self.shared.value = -1
        elif self.play.GetValue() == True or button_label == "Hardware Test":
            if button_label == "Hardware Test":
                self.Enable()
                self.hardware_test = True
                self.hardware_test_panel.Show()
                if not self.task_active:
                    is_success = self.lj.start_labjack()
                self.msgq.put("hardware_test")
                if not is_success:
                    logger.error("Error loading labjack_stream")
                else:
                    self.labjack_stream_button.SetValue(True)
                    self.labjack_stream_button.Enable(False)
                    self.labjack_stream_button.SetLabel("Stop Labjack")
            if not self.liveTimer.IsRunning():
                self.cams.live_start()
                self.liveTimer.Start(150)
                self.play.SetLabel('Stop')
                self.hardware_button.SetLabel("End Test")
            self.set_crop.Enable(False)
            self.rec.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.update_settings.Enable(False)

        else:
            self.shared.value = -1
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()
            self.cams.live_stop()
            self.play.SetLabel('Live')
            self.hardware_button.SetLabel("Hardware Test")
            if self.hardware_test:
                self.cam_test.value = False
                self.hardware_test = False
                self.focus_test.Enable(True)
                self.focus_test.SetValue(False)
                self.contrast_test.SetValue(False)
                self.contrast_test.Enable(True)
                self.set_focus(event)
                self.set_contrast(event)
                self.finish.value = 2
                self.hardware_test_panel.Hide()
                self.hardware_test = False
                if self.task_active:
                    self.labjack_scan_rate = self.lj.stop_labjack()
                    self.labjack_stream_button.Enable(True)
                    if self.labjack_stream_button.GetValue():
                        self.labjack_stream_button.SetValue(False)
                        self.labjack_stream_button.SetLabel("Stream Labjack")
                    self.labjack_stream_button.Enable(True)
            buttons = [self.set_crop, self.rec, self.minRec, self.secRec, self.update_settings]
            self.enable_group(buttons, False)
        
        
    def hardwareFeed(self, event):
        # clicked_button = event.GetEventObject()
        # button_label = clicked_button.GetLabel()
        self.Enable()
        if self.hardware_button.GetValue():
            self.hardware_test = True
            self.hardware_test_panel.Show()
            self.msgq.put("hardware_test")
            if not self.task_active:
                is_success = self.lj.start_labjack()
            
                if not is_success:
                    logger.error("Error loading labjack_stream")
                else:
                    self.labjack_stream_button.SetValue(True)
                    self.labjack_stream_button.Enable(False)
                    self.labjack_stream_button.SetLabel("Stop Labjack")
            if not self.liveTimer.IsRunning():
                self.cams.live_start()
                self.liveTimer.Start(150)
                self.play.SetLabel('Stop')
                self.hardware_button.SetLabel("End Test")
            self.set_crop.Enable(False)
            self.rec.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.update_settings.Enable(False)
            self.task_button.Enable(False)
        else:
            self.shared.value = -1
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()
            self.cams.live_stop()
            self.play.SetLabel('Live')
            self.hardware_button.SetLabel("Hardware Test")
            if self.hardware_test:
                self.cam_test.value = False
                self.hardware_test = False
                self.focus_test.Enable(True)
                self.focus_test.SetValue(False)
                self.contrast_test.SetValue(False)
                self.contrast_test.Enable(True)
                self.set_focus(event)
                self.set_contrast(event)
                self.finish.value = 2
                self.hardware_test_panel.Hide()
                self.hardware_test = False
                if not self.task_active:
                    self.labjack_scan_rate = self.lj.stop_labjack()
                    self.labjack_stream_button.Enable(True)
                    if self.labjack_stream_button.GetValue():
                        self.labjack_stream_button.SetValue(False)
                        self.labjack_stream_button.SetLabel("Stream Labjack")
                        self.labjack_stream_button.Enable(True)
            self.set_crop.Enable(True)
            self.rec.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.update_settings.Enable(True)
            self.task_button.Enable(True)
            
            
    def add_metadata(self):
        metadata = MetadataPanel()
        params = None
        try:
            params = json.loads(self.resultsq.get())
        except:
            pass
        if metadata.show() == wx.ID_OK:
            self.meta,ruamelFile = file_utils.metadata_template()
            date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
            cameras = {}
            self.meta["version"] = str(__version__)
            self.meta["actual_scan_rate"]=self.labjack_scan_rate
            for ndx, s in enumerate(self.cams.camStrList):
                # framerate, exposure = self.cam[ndx].get_actual_settings()
                camset = {'serial':self.cam_cfg[s]['serial'],
                      'ismaster':self.cam_cfg[s]['ismaster'],
                      'crop':self.cam_cfg[s]['crop'],
                      'exposure': self.cam_cfg[s]['exposure'],
                      'framerate': self.cam_cfg[s]['framerate'],
                      'bin': self.cam_cfg[s]['bin'],
                      'nickname': self.cam_cfg[s]['nickname'],
                      'actual_framerate': self.cams.rate[ndx],
                      'actual_exposure': self.cams.exposure[ndx]}
                cameras[s] = camset
            self.meta['cameras'] = cameras
            self.meta['unitRef']=self.user_cfg['unitRef']
            self.meta['Collection']='info'
            self.meta['hardware'] = self.user_cfg['hardware']
            self.meta['screen_settings'] = self.user_cfg['screen_settings']
            meta_name = '%s_%s_%s_metadata.yaml' % (date_string, self.user_cfg['unitRef'], self.sess_string)
            self.metapath = os.path.join(self.sess_dir,meta_name)
    
            self.meta['StartTime']= self.start_time
            self.meta['administrator_id'] = self.launch_args["administrator_id"]
            self.meta["participant_id"] = self.launch_args["participant_id"]
            self.meta["participant_details"] = self.launch_args["participant_detail"]
            
            self.meta['task'] = self.task
            self.meta['task_settings'] = self.task_cfg[self.task]["settings"]
            
            self.meta['trial_data'] = params
            if self.task == "verbal_fluency":
                self.meta["trial_data"]["categories"] = self.trial_panel.add_metadata()
            if self.task == "sara":
                self.meta["trial_data"] = self.trial_panel.add_metadata()

            for data in metadata.data:
                self.meta[data] = metadata.data[data]
                logger.debug(data)
            self.meta['EndTime']= self.end_time
            file_utils.write_metadata(self.meta, self.metapath)
        else:
            #remove entire directory
            logger.debug(self.sess_dir)
            shutil.rmtree(self.sess_dir)
            
    
    def create_file(self):
        date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
        self.base_dir = os.path.join(RAW_DATA_DIR, date_string, self.user_cfg['unitRef'])
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        
        prev_expt_list = [name for name in os.listdir(self.base_dir) if name.startswith('session')]
        file_count = len(prev_expt_list)+1
        self.sess_string = '%s%03d' % ('session', file_count)
        self.sess_dir = os.path.join(self.base_dir, self.sess_string)
        if not os.path.exists(self.sess_dir):
            os.makedirs(self.sess_dir)
        
  
    def initCams(self, event):
        if self.init.GetValue() == True:
            success = self.cams.initialize(event)
            
            if not success:
                return
            self.init.SetLabel('Release')
            self.exposure_button.Enable(True)
            self.play.Enable(True)
            self.rec.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.update_settings.Enable(True)
            self.crop.Enable(False)
            self.reset.Enable(False)
            self.Enable(True)
            
            self.task_button.Enable(True)
            # self.figure.canvas.draw()
            self.image_panel.draw()
        else:
            self.init.SetLabel('Enable')
            self.cams.deinitialize()
            # if self.serSuccess:
            #     self.ser.close()
            if self.rec.GetValue():
                self.rec.SetValue(False) 
                self.cams.recordCam(event)
            if self.play.GetValue():
                self.play.SetValue(False) 
                self.cams.liveFeed(event)
            if self.set_crop.GetValue():
                self.set_crop.SetValue(False)

            self.image_panel.draw()
            self.set_crop.Enable(False)
            self.play.Enable(False)
            self.rec.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.crop.Enable(True)
            self.reset.Enable(True)
            self.update_settings.Enable(False)
            # self.cams.deinitThreads()
        return True          
    
    def tens_pulse(self, event):
        self.serial_device.write("A")
    
    def quitButton(self, event):
        """
        Quits the GUI
        """
        logger.info('Close event called')
        try:
            self.msgq.put("close")
            self.thread.join()
        except:
            logger.debug('no current stimulus thread')

        try:
            self.trial_panel.close_task_panel()
            self.trial_panel.Destroy()
        except:
            pass
        self.ctrl_panel.Destroy()
        self.statusbar.SetStatusText("")
        self.Destroy()

    
    def Hide(self, event):
        self.is_hidden = True
        self.lj.stop_labjack()
        
        self.rest_timer.Stop()
        self.video_status.value = 4
        if self.recording:
            self.cams.stop_recording(event)
        if self.play.GetValue():
            self.play.SetValue(False)
            self.liveFeed(event)
        if self.rec.GetValue():
            self.rec.SetValue(False)
            self.recordCam(event)
        # If running a task    
        if self.hardware_button.GetValue():
            self.hardware_button.SetValue(False)
            self.liveFeed(event)
        if self.task_button.GetValue():
            self.task_button.SetValue(False)
            self.run_task(event)
        if self.init.GetValue():
            self.init.SetValue(False)
            self.initCams(event)
        super().Hide()
        return True
        
    
    def update_crop(self, event):
        value = True if self.crop.GetValue() else False
        self.cams.update_crop(value)
    
        
    def recordCam(self, event):
        if self.rec.GetValue():
            if self.recording:
                return
            self.recording = True
            self.cams.start_recording(event, self.base_dir, self.sess_dir, self.user_cfg['unitRef'], self.sess_string, self.count)
            self.set_crop.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.update_settings.Enable(False)
            self.rec.SetLabel('Stop')
            self.play.SetLabel('Abort')
        else:
            if not self.recording:
                return
            self.recording = False
            self.cams.stop_recording(event)
            self.rec.SetLabel('Record')
            self.play.SetLabel('Play')
            self.set_crop.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.update_settings.Enable(True)
        
        
    def onClick(self,event):
        if self.set_crop.GetValue():
            self.cam_crop.adjust_crop(event, self.axes, self.camStrList, self.cam_cfg)
            self.cam_crop.drawROI(self.axes)
            self.figure.canvas.draw()
    
        
    def OnKeyPressed(self, event):
        keyCode = event.GetKeyCode()
        # Save the new ROI parameters
        if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            # Write the new parameters to the user config file
            if self.set_crop.GetValue():
                self.cam_crop.create_crop(self.cam_config, self.camStrList, self.cam_config)
            file_utils.write_config(self.user_cfg)
            self.set_crop.SetValue(False)
            self.widget_panel.Enable(True)
            self.play.SetFocus() 
        # Modify existing ROI parameters
        elif self.set_crop.GetValue() == True and keyCode in (314, 316, 315, 317, 65, 83, 127):
            self.cam_crop.set_key_crop(self.axes, keyCode)
            self.cam_crop.drawROI(self.axes)       
            self.figure.canvas.draw()
        # Any other case
        else:
            event.Skip() 
        return
        
    
    def show(self, launch_args, event):
        # event = None!
        self.labjack_scan_rate = None
        self.cams.reset_variables()
        self.hardware_test = False
        self.cam_test.value = False
        self.user_cfg = file_utils.read_config('userdata.yaml')
        self.task_cfg = read_config("taskconfig.yaml")
        self.task = launch_args["task"].strip()
        self.msgq.put("update_task")
        self.msgq.put(launch_args["task"].strip())
        self.launch_args = launch_args
        args = {}
        self.video_status.value = 0
        self.task_metadata = launch_args
        self.cam_cfg = {}
        if not self.task or self.task not in self.task_cfg.keys():
            args = self.user_cfg["hardware"]
            self.cam_cfg = self.user_cfg["cameras"]
            self.widget_panel.show_cams()
        else:
            hardware_list = self.task_cfg[self.task]["settings"]
            self.widget_panel.hide_cams()
            for hardware in hardware_list:
                if hardware in self.user_cfg["hardware"].keys():
                    args[hardware] = self.user_cfg["hardware"][hardware]
                elif hardware in self.user_cfg["cameras"].keys():
                    self.cam_cfg[hardware] = self.user_cfg["cameras"][hardware]
        hardware_tuple = [(arg, args[arg]["labjack_input"], args[arg]["graph"], args[arg]["voltage_range"]) for arg in args]
        sorted_hardware = sorted(hardware_tuple, key=lambda item: item[1])
        hardware_lists = list(zip(*sorted_hardware))
        self.hardware_list = hardware_lists
        self.cams.setup(self.cam_cfg, self.user_cfg['isunconnected'])
        self.init.SetValue(True)
        self.widget_panel.update_task(self.task)
        self.trial_panel = self.widget_panel.get_trial_panel()
        self.trial_button = self.trial_panel.continue_button
        try:
            self.repeat_button = self.trial_panel.repeat_trial
            self.repeat_button.Bind(wx.EVT_TOGGLEBUTTON, self.repeat_event)
        except:
            pass
        self.trial_button.Bind(wx.EVT_TOGGLEBUTTON, self.trial_event)
        self.initCams(event)
        self.lj.update_hardware(hardware_lists)
        self.press_count.value = 0 
        self.video_start, self.video_pause = self.trial_panel.get_video_buttons()
        if self.video_start != None:
            self.video_start.Bind(wx.EVT_TOGGLEBUTTON, self.play_instructions)
            self.video_pause.Bind(wx.EVT_TOGGLEBUTTON, self.pause_instructions)
            if self.task == "diadochokinesis" or self.task == "vowel_space":
                self.trial_panel.syllable_start_video_button.Bind(wx.EVT_TOGGLEBUTTON, self.play_instructions)
                self.trial_panel.syllable_pause_video_button.Bind(wx.EVT_TOGGLEBUTTON, self.pause_instructions)
            if self.task == "vowel_space":
                self.trial_panel.next_button.Bind(wx.EVT_BUTTON, self.next_trial)
        super().Show()
        return True
        
        
    def disable_gui(self, event):
        handle = event.GetEventObject()
        if handle == self.task_button:
            self.Bind(wx.EVT_TIMER, self.run_task, self.disable_timer)
        if handle == self.hardware_button:
            self.Bind(wx.EVT_TIMER, self.hardwareFeed, self.disable_timer)
        if handle == self.labjack_stream_button:
            self.Bind(wx.EVT_TIMER, self.labjack_stream, self.disable_timer)
        self.Disable()
        self.disable_timer.StartOnce(80)


    def labjack_stream(self,event):
        self.lj.labjack_stream(event)
        self.Enable()
    
    
    def enable_group(self,buttons, value):
        for button in buttons:
            button.Enable(value)