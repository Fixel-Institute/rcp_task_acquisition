import wx
import wx.lib.scrolledpanel as scrolled

from rcp_task_acquisition.panels.HardwarePanel import HardwarePanel
from rcp_task_acquisition.utils.file_utils import read_config
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/LaunchPanel") 


class LaunchPanel():
    '''
    The initial launch panel where the user sets up the basic metadata and selects
    the protocol to run.
    
    Attributes:
        task (str):
            Current task name (based on taskconfig names)
        task_list (list[int]):
            list of tasks from the taskconfig.yaml
        protocol_choice (wx.Choice):
            dropdown for the possible task selections
        administrator_id (wx.TextCtrl):
            text box for the administrator id. final string will be added to the metadata
        participant_id (wx.TextCtrl):
            text box for the participant id. final string will be added to the metadata
        participant_detail (wx.TextCtrl):
            text box for any overarching participant notes. final string will be added to the metadata
    '''
    def __init__(self, parent=None):
        self.args = None
        self.task = None
        self.is_hidden = False
        task_config = read_config("taskconfig.yaml")
        self.task_list = list(task_config.keys())
        self.task_list.append("all_hardware")
        self.protocol_choice = None
        self.metadata = {"task": None,
                         "administrator_id": None,
                         "participant_id": None,
                         "participant_detail": None}
        # Basic panel set up. 3 different steps (Protocol, metadata and buttons) to help with 
        # organization and padding between sections
        
        
        self.regular_size = wx.Size(650, 400)
        self.hardware_size = wx.Size(650,800)
        button_width = wx.Size(200, -1)
        
        self.dialog = wx.Dialog(parent, id= wx.ID_ANY, title= 'Select Protocol',
                            size = self.regular_size, pos = (660, 275))
        
        self.panel = scrolled.ScrolledPanel(self.dialog, -1,style=wx.SUNKEN_BORDER)
        self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.hardware_panel = HardwarePanel(task_config, self.panel)
        self.hardware_panel.Hide()
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_protocol(button_width), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, 10)
        vertical_sizer.Add(self._setup_metadata(), 0, wx.EXPAND | wx.ALL, 10)
        vertical_sizer.Add(self._setup_buttons(button_width), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        vertical_sizer.Add(self.hardware_panel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        self.panel.SetSizerAndFit(vertical_sizer)

        
    def _setup_protocol(self, button_width):
        self.protocol_text = wx.StaticText(self.panel, label='Protocol:')
        self.protocol_choice= wx.Choice(self.panel, 
                                       id=wx.ID_ANY, 
                                       choices=self.task_list,
                                       size=(200, -1))
        self.protocol_choice.Bind(wx.EVT_CHOICE, self.task_event)
        self.protocol_choice.SetSelection(0)
        self.protocol_button = wx.Button(self.panel, size=button_width, label="Select Protocol")
        self.task_event("")
        grid_sizer = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer.Add(self.protocol_text, 0, flag= wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
        grid_sizer.Add(self.protocol_choice, 0, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
        grid_sizer.Add(self.protocol_button, 0, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
        return grid_sizer
    
    
    def _setup_metadata(self):
        self.administrator_text = wx.StaticText(self.panel, label='Administrator Id:')
        self.administrator_id =  wx.TextCtrl(self.panel, size=wx.Size(450, -1), style=wx.TE_LEFT, value="")
        
        self.participant_id_text = wx.StaticText(self.panel, label='Participant Id:')
        self.participant_id = wx.TextCtrl(self.panel, size=wx.Size(450, -1), style=wx.TE_LEFT, value="")
        
        self.participant_detail_text = wx.StaticText(self.panel, label='Participant Details:')
        self.participant_detail = wx.TextCtrl(self.panel, size=wx.Size(450, 70), style=wx.TE_MULTILINE | wx.TE_LEFT, value="")
       
        grid_sizer = wx.GridBagSizer(4, 3)
        grid_sizer.Add(self.administrator_text, pos=(0,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.administrator_id, pos=(0,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_id_text, pos=(1,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_id, pos=(1,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_detail_text, pos=(2,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_detail, pos=(2,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        return grid_sizer


    def _setup_buttons(self, button_width):
        self.hardware_button = wx.ToggleButton(self.panel, size=button_width, label="Update Hardware")
        self.hardware_button.Bind(wx.EVT_TOGGLEBUTTON, self.hardware_event)
        
        self.compress_button = wx.Button(self.panel, size=button_width, label="Compress Videos")
        self.compress_button.Enable(False)
        
        self.exit_button = wx.Button(self.panel, size=button_width, label="Exit")        
        
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(self.hardware_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_sizer.Add(self.compress_button , 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_sizer.Add(self.exit_button, 0, wx.ALIGN_CENTER_VERTICAL)
        return row_sizer
    
    
    def enable_gui(self, is_enabled) -> None:
        self.hardware_button.Enable(is_enabled) 
        # self.compress_button.Enable(is_enabled)
        self.exit_button.Enable(is_enabled)
        self.administrator_text.Enable(is_enabled)
        self.administrator_id.Enable(is_enabled)
        self.participant_id_text.Enable(is_enabled)
        self.participant_id.Enable(is_enabled)
        self.participant_detail_text.Enable(is_enabled)
        self.participant_detail.Enable(is_enabled)
        self.protocol_button.Enable(is_enabled)
        self.protocol_choice.Enable(is_enabled)
        self.protocol_text.Enable(is_enabled)
        self.hardware_button.SetValue(False)
        self.hardware_button.SetLabel("Update Hardware")
        self.panel.Update()
        
        
    def exit_event(self)-> None:
        logger.debug("exit")
        self.panel.Destroy()
        self.dialog.Destroy()
    
    
    def protocol_event(self, event: wx.Event) -> None:
        '''
        Bound to select protocol event. Triggers starting the aquisition
        gui.
        '''
       
        self.metadata = {"task": None,
                         "administrator_id": None,
                         "participant_id": None,
                         "participant_detail": None}
        self.metadata["task"] = self.task.strip()
        self.metadata["administrator_id"] = self.administrator_id.GetValue() 
        self.metadata["participant_id"] = self.participant_id.GetValue()
        self.metadata["participant_detail"] = self.participant_detail.GetValue()
        
        self.is_hidden = True
        self.dialog.Hide()


    def hardware_event(self, event):
        '''
        triggers showing the hardware panel

        '''
        is_pressed = self.hardware_button.GetValue()
        if is_pressed:
            self.hardware_button.SetLabel("Close Hardware Panel")
            self.hardware_panel.Show()
            self.dialog.SetSize(self.hardware_size)
            self.panel.SetupScrolling(scroll_x=False, scroll_y=True, scrollToTop=False, scrollIntoView=False)
            self.hardware_panel.reset_hardware()
            
        else:
            self.hardware_button.SetLabel("Update Hardware")
            self.hardware_panel.Hide()
            self.dialog.SetSize(self.regular_size)
            self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.dialog.CenterOnScreen()

        
    def task_event(self, event):
        self.task = self.task_list[self.protocol_choice.GetCurrentSelection()]
        self.hardware_panel.set_task(self.task)


    def Show(self):
        self.is_hidden = False
        return self.dialog.Show()
    
    
    def get_metadata(self) -> None: 
        self.protocol_button.Enable(False)
        self.hardware_panel.Hide()
        self.dialog.SetSize(self.regular_size)
        self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.hardware_button.Enable(False)
        self.panel.Refresh()
        self.metadata["task"] = self.task
        self.metadata["administrator_id"] = self.administrator_id.GetValue() 
        self.metadata["participant_id"] = self.participant_id.GetValue()
        self.metadata["participant_detail"] = self.participant_detail.GetValue()
        
    
    def Hide(self):
        self.dialog.Hide()
    


    