from  panels.LaunchPanel import LaunchPanel
from panels.MainFrame import MainFrame
import time

import multiCam_DLC.compressVideos_v3 as compressVideos
import wx
from models.Warnings import Warning
from utils.logger import get_logger
logger = get_logger("./panels/SwitchPanel") 


class SwitchPanel():
    def __init__(self):
        self.launch_showing = True
        self.launch_panel = LaunchPanel()
        self.task_frame = MainFrame(None)
        self.warning = Warning() 
        self.launch_panel.show()
        self.launch_panel.protocol_button.Bind(wx.EVT_BUTTON, self.disable_panel)
        self.launch_panel.exit_button.Bind(wx.EVT_BUTTON, self.exit_event)
        self.task_frame.quit.Bind(wx.EVT_BUTTON, self.disable_panel)
        self.launch_panel.compress_button.Bind(wx.EVT_BUTTON, self.compress_video)
        self.task_frame.Bind(wx.EVT_CLOSE, self.disable_panel)
        self.launch_panel.dialog.Bind(wx.EVT_CLOSE, self.exit_event)
        self.disable_timer = wx.Timer(self.launch_panel.panel, wx.ID_ANY)
        self.launch_panel.panel.Bind(wx.EVT_TIMER, self.switch_panel, self.disable_timer)
        self.task_frame.Bind(wx.EVT_TIMER, self.switch_panel, self.disable_timer)
        self.launch_panel.panel.SetFocus()
        # self.launch_panel.compress_button.Enable(False)
        
    def switch_panel(self, event):
        if not self.launch_showing:
            self.launch_panel.panel.Enable()
            self.launch_panel.protocol_button.SetLabel("Select Protocol")
            self.launch_panel.hardware_button.Enable(True)
            self.launch_panel.protocol_button.Enable(True)
            self.task_frame.hide(event)
            self.launch_panel.show()
        else:
            self.task_frame.Enable()
            self.task_frame.quit.SetLabel("Exit to Launch Menu")
            self.launch_panel.get_metadata()
            launched = self.task_frame.show(self.launch_panel.metadata, event)
            if launched:
                self.launch_panel.hide()
        self.launch_showing = not self.launch_showing

    def disable_panel(self, event):
        if not self.launch_showing:
            self.task_frame.quit.SetLabel("Loading...")
            self.task_frame.Disable()
        else:
            self.launch_panel.protocol_button.SetLabel("Loading...")
            self.launch_panel.panel.Disable()
        self.disable_timer.StartOnce(80)
        
        
    def exit_event(self, event):
        try:
            if self.compressThread.is_alive():
                               
                self.warning.update_error("compression")
                self.warning.display()
                return
            
            self.compressThread.terminate()   
        except:
            pass
        self.launch_panel.exit_event()
        self.task_frame.hide(event)
        self.task_frame.quitButton(event)


    def compress_video(self, event):
        ok2compress = False
        try:
            if not self.mv.is_alive():
                self.mv.terminate()   
                ok2compress = True
            else:
                if wx.MessageBox("Compress when transfer completes?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                    while self.mv.is_alive():
                        time.sleep(10)
                    self.mv.terminate()   
                    ok2compress = True
        except:
            ok2compress = True
            
        if ok2compress:
            self.warning.update_error("compress")
            logger.info('\n\n---- Please DO NOT close this GUI until compression is complete!!! ----\n\n')
            self.compressThread = compressVideos.CLARA_compress()
            self.compressThread.start()
            self.launch_panel.compress_button.Enable(False)