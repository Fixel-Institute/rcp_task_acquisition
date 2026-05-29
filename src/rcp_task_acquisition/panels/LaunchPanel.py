import wx
import wx.lib.scrolledpanel as scrolled

from rcp_task_acquisition.panels.HardwarePanel import HardwarePanel
from rcp_task_acquisition.utils.file_utils import read_config
from rcp_task_acquisition.panels.ParticipantPanel import ParticipantPanel
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
        participant_id (wx.ComboBox):
            Drop down to select the participants. the participant Id will be added to the metadata, the rest of the info is stored in a db
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
        self.participant_panel = ParticipantPanel(None)
        self.current_list = []
        self.regular_size = wx.Size(650, 400)
        self.hardware_size = wx.Size(650,800)
        button_width = wx.Size(220, -1)
        self.update_list_bool = True
        self.ignore_pop_up = False
        self.dialog = wx.Dialog(parent, id= wx.ID_ANY, title= 'Select Protocol',
                            size = self.regular_size, pos = (660, 275))
        
        self.panel = scrolled.ScrolledPanel(self.dialog, -1,style=wx.SUNKEN_BORDER)
        self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.hardware_panel = HardwarePanel(task_config, self.panel)
        self.hardware_panel.Hide()
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_metadata(button_width), 0, wx.EXPAND | wx.ALL, 10)
        vertical_sizer.Add(self._setup_buttons(button_width), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        vertical_sizer.Add(self.hardware_panel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        self.panel.SetSizerAndFit(vertical_sizer)
    
    
    def get_participants(self, event):
        self.participant_list, self.participant_tuple = self.participant_panel.get_all_participants()
        print(f"list: {self.participant_list}, tuple: {self.participant_tuple}")
        self.participant_id.SetItems(self.participant_list)
    
    def _setup_metadata(self, button_width):
        self.protocol_text = wx.StaticText(self.panel, label='Protocol:')
        self.protocol_choice= wx.Choice(self.panel, 
                                       id=wx.ID_ANY, 
                                       choices=self.task_list,
                                       size=(220, -1))
        self.protocol_choice.Bind(wx.EVT_CHOICE, self.task_event)
        self.protocol_choice.SetSelection(0)
        self.protocol_button = wx.Button(self.panel, size=button_width, label="Select Protocol")
        self.task_event("")
        
        self.administrator_text = wx.StaticText(self.panel, label='Administrator Id:')
        self.administrator_id =  wx.TextCtrl(self.panel, size=wx.Size(450, -1), style=wx.TE_LEFT, value="")
        
        self.participant_id_text = wx.StaticText(self.panel, label='Participant:')
        self.participant_id =  wx.ComboBox(self.panel, size=wx.Size(450, -1), style=wx.CB_DROPDOWN, choices=[])
        self.get_participants(None)
        self.participant_id.Bind(wx.EVT_TEXT, self.update_list)
        self.participant_id.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        # self.participant_id.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.on_dropdown)
        self.participant_remove = wx.Button(self.panel, size=button_width, label="Remove Participant")
        self.participant_add = wx.Button(self.panel, size=button_width, label= "Add New Participant")
        self.participant_add.Bind(wx.EVT_BUTTON, self.add_participant)
        self.participant_remove.Bind(wx.EVT_BUTTON, self.remove_participants)
        self.participant_detail_text = wx.StaticText(self.panel, label='Participant Details:')
        self.participant_detail = wx.TextCtrl(self.panel, size=wx.Size(450, 70), style=wx.TE_MULTILINE | wx.TE_LEFT, value="")
       
        grid_sizer = wx.GridBagSizer(4, 3)
        grid_sizer.Add(self.protocol_text,  pos=(0,0), span=(0,1),  flag= wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.protocol_choice,  pos=(0,1), span=(0,1),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.protocol_button, pos=(0,2), span=(0,1),  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.administrator_text, pos=(1,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.administrator_id, pos=(1,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_id_text, pos=(2,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_id, pos=(2,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_remove, pos=(3,1), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_add, pos=(3,2), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        
        grid_sizer.Add(self.participant_detail_text, pos=(4,0), span=(0,1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        grid_sizer.Add(self.participant_detail, pos=(4,1), span=(0,3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        return grid_sizer


    def _setup_buttons(self, button_width):
        button_width = wx.Size(200, -1)
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
    

        
    def update_list(self, event):
        if self.ignore_pop_up:
            self.ignore_pop_up = False
            return
        
        if self.update_list_bool:
            self.update_list_bool = False
            current_text = self.participant_id.GetValue()
            
            print(f"current_text: {current_text}")
            test_text = current_text.replace(" ", "").lower()
            if test_text == "":
                current_text = test_text
            self.current_list = [item for item in self.participant_list if test_text in item.lower().replace(" ", "")]
            # self.participant_id.Clear()
            self.participant_id.SetItems(self.current_list)
            self.participant_id.ChangeValue(current_text)
            self.participant_id.Popup()
            self.participant_id.SetInsertionPointEnd()
            self.update_list_bool = True
    

    def on_enter(self, event):
        pass

            
    def remove_participants(self, event):
        self.ignore_pop_up = True
        user_string, user_index = "", -1
        
        id_string = self.current_list[self.participant_id.GetSelection()]
        for user_index, user_string in enumerate(self.participant_list):
            if user_string == id_string:
                user = user_string
                index = user_index
                break
        # user = self.participant_list[index]
        if index == -1:
            return
        id_to_delete = self.participant_tuple[index][0]
        dlg = wx.MessageDialog(None, 
                               f"Are you sure you want to delete {user}?", 
                               "Warning", 
                               wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_NO: 
            return
        
        self.participant_panel.remove_participant(id_to_delete)
        self.participant_id.SetSelection(-1)
        self.get_participants(None)
    
    
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
        self.participant_panel.exit_event()
        self.dialog.Destroy()
    
    
    def add_participant(self, event):
        self.ignore_pop_up = True
        self.participant_panel.show()
        
        participant_id = self.participant_panel.data
        # self.update_list_bool = False
        new_index = -1
        self.get_participants(None)
        for index, current_id in enumerate(self.participant_tuple):
            print(f"here: {index}, {current_id}")
            if current_id[0] == participant_id:
                new_index = index
        self.participant_id.SetSelection(new_index)
        
    
    def protocol_event(self, event: wx.Event) -> None:
        '''
        Bound to select protocol event. Triggers starting the aquisition
        gui.
        '''
        participant_index = self.participant_id.GetSelection()
        participant_id = self.participant_tuple[participant_index][0] 
        if participant_index == -1:
            participant_id = ""
        self.metadata = {"task": None,
                         "administrator_id": None,
                         "participant_id": None,
                         "participant_detail": None}
        self.metadata["task"] = self.task.strip()
        self.metadata["administrator_id"] = self.administrator_id.GetValue() 
        self.metadata["participant_id"] = participant_id
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
        participant_index = self.participant_id.GetSelection()
         
        if participant_index == -1:
            participant_id = ""
        else:
            participant_id = self.participant_tuple[participant_index][0]
        self.protocol_button.Enable(False)
        self.hardware_panel.Hide()
        self.dialog.SetSize(self.regular_size)
        self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.hardware_button.Enable(False)
        self.panel.Refresh()
        self.metadata["task"] = self.task
        self.metadata["administrator_id"] = self.administrator_id.GetValue() 
        self.metadata["participant_id"] =  participant_id
        self.metadata["participant_detail"] = self.participant_detail.GetValue()
        
    
    def Hide(self):
        self.dialog.Hide()
    


    