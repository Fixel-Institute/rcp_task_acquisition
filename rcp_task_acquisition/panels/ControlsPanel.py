# -*- coding: utf-8 -*-
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
from rcp_task_acquisition.tasks.UpdrsTap.panel import FingerTapPanel
from rcp_task_acquisition.tasks.NaturalisticSpeech.panel import NaturalisticSpeechPanel
from rcp_task_acquisition.tasks.Diadochokinesis.panel import DdkPanel
from rcp_task_acquisition.tasks.VowelSpace.panel import VowelSpacePanel
from rcp_task_acquisition.tasks.VerbalFluency.panel import VerbalFluencyPanel
from rcp_task_acquisition.tasks.NBack.panel import NbackPanel
from rcp_task_acquisition.tasks.ReachGrasp.panel import ReachGraspPanel
from rcp_task_acquisition.tasks.ToneTaps.panel import ToneTapsClosedPanel
from rcp_task_acquisition.tasks.Sara.panel import SaraPanel
from rcp_task_acquisition.tasks.VerbGeneration.panel import VerbGenerationPanel



class ControlsPanel(wx.Panel):
    def __init__(self,parent, ctrl_panel, task="task"):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
        
        vertical_spacer = wx.GridBagSizer(5, 5)
        vertical_position = 0
        button_width = 76
        self.cam_panel = CameraControlPanel(self, button_width)
        self.task_panel = self.get_task_panel(task) #VowelSpacePanel(self)
        self.task_panel.Enable(False)
        self.hardware_test = ctrl_panel.create_hardware_test_panel(self)
        self.hardware_buttons = (ctrl_panel.contrast_test, ctrl_panel.focus_test)
        vertical_spacer.Add(self._set_up_tasks(task, button_width), pos=(vertical_position, 0), span=(0,5),flag=wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, border=5)
        vertical_position+=1
        vertical_spacer.Add(self.cam_panel, pos=(vertical_position, 0), span=(0,5),flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        
        vertical_position+=1
        vertical_spacer.Add(ctrl_panel.create_labjack_panel(self), pos=(vertical_position,0), span=(0,5), flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        vertical_position+=1
        vertical_spacer.Add(self.hardware_test, pos=(vertical_position,0), span=(0,5), flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_LEFT | wx.ALL, border=5)
        self.SetSizer(vertical_spacer)
        vertical_spacer.Fit(self)
        self.cam_panel.Hide()
        self.hardware_test.Hide()
        self.Layout()


    def get_trial_panel(self):
        return self.task_panel

    
    def show_cams(self):
        return self.cam_panel.Show()

    
    def hide_cams(self):
        return self.cam_panel.Hide()

    
    def _set_up_tasks(self, task, button_width):
        vertical_position = 0
        white_space = 10
        self.task_sizer = wx.GridBagSizer(6, 5)
        self.font = wx.Font(wx.FontInfo(12).Bold())
        task_title = task.replace("_", " ").title()
        self.task_text = wx.StaticText(self, label=f"{task_title}")
        self.task_text.SetFont(self.font)
        self.task_sizer.Add(self.task_text, pos=(vertical_position,0), span=(0,5), flag=wx.ALIGN_CENTER | wx.ALL, border=white_space)
        vertical_position+=1
        
        self.task_sizer.Add(self.task_panel, pos=(vertical_position,0), span=(0,5), flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_LEFT | wx.ALL, border=0)
        vertical_position+=1
                
        self.camera_toggle = wx.Button(self, label="Toggle Cameras", size=(button_width*2, -1))
        self.task_sizer.Add(self.camera_toggle, pos=(vertical_position,0), span=(0,2), flag=wx.LEFT, border=white_space)

        self.hardware_button = wx.ToggleButton(self, id=wx.ID_ANY, label="Hardware Test",size=(button_width*2, -1))
        self.task_sizer.Add(self.hardware_button, pos=(vertical_position,2), span=(0,2), flag=wx.LEFT, border=white_space)
        
        vertical_position+=1
        
        self.tens_button = wx.Button(self, id=wx.ID_ANY, label="TENS Test",size=(button_width*2, -1))
        self.task_sizer.Add(self.tens_button, pos=(vertical_position,0), span=(0,2), flag=wx.LEFT, border=white_space)
        
        vertical_position+=1
                
        self.session_button = wx.ToggleButton(self, id=wx.ID_ANY, label="Start Task",size=(button_width*4+15, -1))
        self.task_sizer.Add(self.session_button, pos=(vertical_position,0), span=(0,4), flag=wx.LEFT, border=white_space)
        
        vertical_position+=1

        self.quit = wx.Button(self, id=wx.ID_ANY, label="Exit to Launch Menu",size=(int(button_width*4+15), -1))
        self.task_sizer.Add(self.quit, pos=(vertical_position,0), span=(0,4), flag=wx.LEFT, border=white_space)

        return self.task_sizer
    
    
    def get_cam_handles(self):
        return (self.cam_panel.init,self.cam_panel.reset,self.cam_panel.update_settings,self.cam_panel.play,self.cam_panel.rec,
                self.cam_panel.exposure_button,self.cam_panel.set_crop,self.cam_panel.crop, self.cam_panel.minRec,self.cam_panel.secRec)


    def get_hardware_handles(self): 
        return (self.hardware_buttons[0], self.hardware_buttons[1], self.hardware_test)
    
    
    def get_task_handles(self):
        return (self.camera_toggle, self.hardware_button, self.session_button, self.quit, self.tens_button)
    

    def update_task(self, task):    
        task_title = task.replace("_", " ").title()
        self.task_text.SetLabel(f"{task_title}")
        self.task_panel.Destroy()
        self.task_panel = self.get_task_panel(task)
        
        self.task_sizer.Add(self.task_panel, pos=(1,0), span=(0,5), flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_LEFT | wx.ALL, border=0)
        self.task_panel.Hide()
        self.Layout()
        
        
    def get_task_panel(self, task):
        if task == "motor_task_finger_taps":
            return FingerTapPanel(self)
        elif task == "tone_taps":
            panel = FingerTapPanel(self)
            panel.seconds_text.Hide() 
            return panel
        elif task == "naturalistic_speech":
            return NaturalisticSpeechPanel(self)
        elif task == "diadochokinesis":
            return DdkPanel(self)
        elif task == "vowel_space":
            return VowelSpacePanel(self)
        elif task == "verbal_fluency":
            return VerbalFluencyPanel(self)
        elif task == "n_back":
            return NbackPanel(self)
        elif task == "reach_grasp":
            return ReachGraspPanel(self)
        elif task == "tone_taps_closed":
            return ToneTapsClosedPanel(self)
        elif task == "sara":
            return SaraPanel(self)
        elif task == "verb_generation":
            return VerbGenerationPanel(self)
        else:
            basic_panel = TrialPanel(self)
            basic_panel.continue_button.Show()
            return basic_panel 
    
    
    def close_task_panel(self):
        self.task_panel.Destroy()
    
    
    
class CameraControlPanel(wx.Panel):
    def __init__(self, parent, button_width):
        wx.Panel.__init__(self, parent, -1,style=wx.BORDER_NONE)
        camctrlbox = wx.StaticBox(self, label="Camera Control")
        camsizer = wx.GridBagSizer(5, 5)
        bsizer = wx.StaticBoxSizer(camctrlbox, wx.HORIZONTAL)
        white_space = 0
        vpos = 0
        
        self.init = wx.ToggleButton(self, id=wx.ID_ANY, label="Enable", size=(button_width,-1))
        camsizer.Add(self.init, pos=(vpos,0), span=(1,2), flag=wx.ALL, border=white_space)
        
        self.reset = wx.Button(self, id=wx.ID_ANY, label="Reset", size=(button_width, -1))
        camsizer.Add(self.reset, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=white_space)
        
        self.update_settings = wx.Button(self, id=wx.ID_ANY, label="Update Settings", size=(button_width*2, -1))
        camsizer.Add(self.update_settings, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=white_space)
        self.update_settings.Enable(False)
        
        vpos+=1
        self.play = wx.ToggleButton(self, id=wx.ID_ANY, label="Live", size=(button_width, -1))
        camsizer.Add(self.play, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=white_space)
        self.play.Enable(False)
        
        self.rec = wx.ToggleButton(self, id=wx.ID_ANY, label="Record", size=(button_width, -1))
        camsizer.Add(self.rec, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=white_space)
        self.rec.Enable(False)

        self.exposure_button = wx.Button(self, id=wx.ID_ANY, label="Set Exposure", size=(button_width*2, -1))
        camsizer.Add(self.exposure_button, pos=(vpos,6), span=(0,6), flag=wx.ALL, border=white_space)
        self.exposure_button.Enable(False)
        
        vpos+=1
        self.set_crop = wx.ToggleButton(self, id=wx.ID_ANY, label="Set Crop")
        camsizer.Add(self.set_crop, pos=(vpos,0), span=(0,3), flag=wx.TOP | wx.BOTTOM, border=3)
        self.set_crop.Enable(False)
        
        self.crop = wx.CheckBox(self, id=wx.ID_ANY, label="Crop", size=(button_width, -1))
        camsizer.Add(self.crop, pos=(vpos,3), span=(0,3), flag=wx.TOP, border=0)
        self.crop.SetValue(True)
            
        self.minRec = wx.TextCtrl(self, value='20', size=(50, -1))
        self.minRec.Enable(False)
        min_text = wx.StaticText(self, label='M:')
        camsizer.Add(self.minRec, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=white_space)
        camsizer.Add(min_text, pos=(vpos,6), span=(1,1), flag=wx.TOP, border=5)
        
        self.secRec = wx.TextCtrl(self, value='0', size=(50, -1))
        self.secRec.Enable(False)
        sec_text = wx.StaticText(self, label='S:')
        camsizer.Add(self.secRec, pos=(vpos,10), span=(1,2), flag=wx.ALL, border=white_space)
        camsizer.Add(sec_text, pos=(vpos,9), span=(1,1), flag=wx.TOP, border=5)
        
        bsizer.Add(camsizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(bsizer)
        bsizer.Fit(self)