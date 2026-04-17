import wx
from enum import Enum

from rcp_task_acquisition.panels.LaunchPanel import LaunchPanel
from rcp_task_acquisition.panels.MainFrame import MainFrame
from rcp_task_acquisition.models.Warnings import Warning
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/SwitchPanel") 



class ActivePanel(Enum):
    LAUNCH = True
    TASK = False


class SwitchPanel():
    def __init__(self) -> None:
        self.active_panel = True
        self.launch_panel = LaunchPanel()
        self.task_frame = MainFrame()
        self.warning = Warning()
        
        self.disable_timer = wx.Timer(self.launch_panel.panel, wx.ID_ANY)
        
        self.task_frame.quit.Bind(wx.EVT_BUTTON, self.disable_panel)
        self.task_frame.Bind(wx.EVT_CLOSE, self.disable_panel)
        
        self.launch_panel.Show()
        self.launch_panel.protocol_button.Bind(wx.EVT_BUTTON, self.disable_panel)
        self.launch_panel.exit_button.Bind(wx.EVT_BUTTON, self.exit_event)
        self.launch_panel.dialog.Bind(wx.EVT_CLOSE, self.exit_event)
        self.launch_panel.panel.Bind(wx.EVT_TIMER, self.switch_panel, self.disable_timer)
        self.task_frame.Bind(wx.EVT_TIMER, self.switch_panel, self.disable_timer)
        self.launch_panel.panel.SetFocus()
        
        

    def switch_panel(self, event: wx.Event) -> None:
        # if launch panel showing, switching to show task panel & vice versa
        if self.active_panel == ActivePanel.LAUNCH.value:
            self.task_frame.Enable()
            self.task_frame.quit.SetLabel("Exit to Launch Menu")
            self.launch_panel.get_metadata()
            self.task_frame.show(self.launch_panel.metadata, event)
            self.launch_panel.Hide()
            
        else:
            self.launch_panel.protocol_button.SetLabel("Select Protocol")
            self.launch_panel.enable_gui(True)
            
            self.task_frame.Hide(event)
            self.launch_panel.Show()
        
        self.active_panel = not self.active_panel


    def disable_panel(self, event: wx.Event) -> None:
        '''
        Disable the current shown panel while enabling other panel
        '''
        if  self.active_panel == ActivePanel.LAUNCH.value:
           self.launch_panel.protocol_button.SetLabel("Loading...")
           self.launch_panel.enable_gui(False)
           
        else:
            self.task_frame.quit.SetLabel("Loading...")
            self.task_frame.Disable()
            
        self.disable_timer.StartOnce(200)
        
        
    def exit_event(self, event: wx.Event) -> None:
        self.launch_panel.exit_event()
        self.task_frame.Hide(event)
        self.task_frame.quitButton(event)



        