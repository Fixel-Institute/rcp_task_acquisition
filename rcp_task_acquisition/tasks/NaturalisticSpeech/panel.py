# -*- coding: utf-8 -*-
import os
import wx

from rcp_task_acquisition.panels.TrialPanel import TrialPanel
import rcp_task_acquisition.tasks.NaturalisticSpeech.constants as c
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/NaturalisticSpeechPanel") 



class NaturalisticSpeechPanel(TrialPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seconds = 0
        self.display_secs = 0
        self.display_mins = 0
        self.trial_number = 1
        self.timestamps ={}
        self.countdown_start = 0
        self.button_width = 76
        self.border = 5
        self.photo = None
        self.selection = 0
        self.image_list = []
        wx.Panel.__init__(self, parent, -1, size=wx.Size(-1,-1))
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._set_up_photo(), 0, wx.ALIGN_LEFT | wx.ALL, self.border)
        self.SetSizer(vertical_sizer)
        self.rest_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.rest_timer)
     

    def _set_up_photo(self):
        '''
        Set up the naturalistic speech panel
        Returns:
            message (wx dialog panel)

        '''
        self.image_names = os.listdir(c.IMG_DIR)
        
        for image in self.image_names:
            try:
                image_path = os.path.join(c.IMG_DIR, image)
                wx_image = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
                wx_image = wx_image.Scale(250, 250)
                self.image_list.append( wx_image.ConvertToBitmap())
                
            except Exception as e:
                logger.error(f"Unable to load {image}, Error: {e}")
        
        self.image_choice= wx.Choice(self, 
                                       id=wx.ID_ANY, 
                                       choices=self.image_names,
                                       size=(310, -1))
        
        self.image_choice.SetSelection(self.selection)
        self.shown_image = wx.StaticBitmap(self, wx.ID_ANY, self.image_list[self.selection])
        self.image_choice.Bind(wx.EVT_CHOICE, self.update_image)
        self.trial_text = wx.StaticText(self, label="Trial # 1")
        
        photo_text = wx.StaticText(self, label='Choose which photo to show:')
        self.seconds_text = wx.StaticText(self, label= "Time: 0 mins, 0 secs")

        grid_sizer = wx.GridBagSizer(5, 4)

        grid_sizer.Add(photo_text, pos=(0, 0), span=(0, 4),flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=10)
        
        grid_sizer.Add(self.trial_text, pos=(1, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        grid_sizer.Add(self.shown_image, pos=(2, 0), span=(0,4), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
        grid_sizer.Add(self.image_choice, pos=(3, 0), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=self.border)
        self.continue_button = wx.ToggleButton(self, label="Begin Trial", size=(self.button_width*2, -1))
        
        grid_sizer.Add(self.seconds_text, pos=(4, 0), span=(0, 4), flag=wx.ALIGN_LEFT |  wx.ALL, border=10)
        grid_sizer.Add(self.continue_button, pos=(5, 0), span=(0, 4), flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        

        return grid_sizer


    def run_trial(self, number):
        self.seconds = 0
        self.trial_number = number
        
        self.trial_is_active = True
        self.image_choice.Enable(False)
        self.shown_image.Enable(False)
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")


    def update_trial(self, number):
        self.trial_number = number
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")
        
    def get_result(self):
        image_path = self.image_names[self.selection] #os.path.join(c.IMG_DIR, self.image_names[self.selection])
        return f"{image_path},{self.trial_number}"

    
    def reset(self, number):
        self.seconds = 0
        self.trial_number = number
        self.trial_is_active = False
        self.seconds_text.SetLabel("Time: 0 mins, 0 secs")
        self.image_choice.Enable(True)
        self.shown_image.Enable(True)
        self.trial_text.SetLabel(f"Trial # {self.trial_number}")
    

    def on_timer(self, event):
        self.seconds+=1
        self.display_mins = int(self.seconds/60)
        self.display_secs = self.seconds%60
        if self.trial_is_active:
            self.seconds_text.SetLabel(f"Time: {self.display_mins} mins, {self.display_secs} secs")


    def update_image(self,event):
        self.selection = self.image_choice.GetSelection()
        self.shown_image.SetBitmap(self.image_list[self.selection])
        self.Layout()


