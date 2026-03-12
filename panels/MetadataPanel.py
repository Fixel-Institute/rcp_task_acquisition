import wx
from dataclasses import dataclass
from dataclasses import dataclass
import wx.lib.scrolledpanel as scrolled
import logging
# Get a logger instance (or the root logger)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@dataclass
class WxObject:
    object: wx.TextCtrl
    type: str


class MetadataPanel():
    def __init__(self, parent=None):
        wx_size = wx.Size(650,275)
        self.metadata = {}
        self.dialog = wx.Dialog(parent, id= wx.ID_ANY, title= 'Metadata Collection',
                            size = wx_size, pos = wx.DefaultPosition)
        self.panel = scrolled.ScrolledPanel(self.dialog, -1,style=wx.SUNKEN_BORDER)
        self.panel.SetupScrolling(scroll_x=False, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        
        
        vertical_sizer.Add(self._setup_metadata(), 0, wx.ALIGN_LEFT | wx.TOP, 30)
        vertical_sizer.Add(self._setup_buttons(), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 30)
        self.panel.SetSizerAndFit(vertical_sizer)
    
    
    def _setup_metadata(self):
        notes_text =  wx.StaticText(self.panel, label='Trial Notes:')
        self.metadata["task_notes"] = WxObject(object=wx.TextCtrl(self.panel, size=wx.Size(520, 100), style=wx.TE_MULTILINE | wx.TE_LEFT),
                                          type="text")
        
        grid_sizer = wx.GridBagSizer(4, 5)
        grid_sizer.Add(notes_text, pos=(0, 0), span=(0,1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
        grid_sizer.Add(self.metadata["task_notes"].object, pos=(0, 1), span=(0,4), flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        return grid_sizer
        
        
    def _setup_buttons(self):
        save = u'\u2714'
        self.continue_button = wx.Button(self.panel, label=f"{save}  Save and Exit")
        self.continue_button.Bind(wx.EVT_BUTTON, self.continue_event)
        cancel= u'\u2717'
        self.cancel_end_button = wx.Button(self.panel, label=f"{cancel}  Delete Session")
        self.cancel_end_button.Bind(wx.EVT_BUTTON, self.cancel_event)
        
        row_sizer = wx.GridBagSizer(3, 2)
        row_sizer.Add(self.continue_button, pos=(0, 0), span=(2,1), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=10)
        row_sizer.Add(self.cancel_end_button, pos=(0, 1), span=(2,1), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=10)
        return row_sizer
    
    
    def get_metadata(self):
        data = {}
        for key in self.metadata:
            if self.metadata[key].type=="text":
                data[key] = self.metadata[key].object.GetValue()
        
        logger.debug(data)
        return data
    
    
    def continue_event(self, event):
        logger.debug("Continue Pressed")
        self.get_metadata()
        self.data = self.get_metadata()
        self.dialog.EndModal(wx.ID_OK)
        self.dialog.Destroy()
    
    
    def cancel_event(self, event):
        logger.debug("Cancel Pressed")
        dlg = wx.MessageDialog(None, 
                               "Are you sure you want to delete this session?", 
                               "", 
                               wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_NO: 
            return
        self.dialog.EndModal(wx.CANCEL)
        self.dialog.Destroy()
    
    
    def show(self):
        return self.dialog.ShowModal()
    



# if __name__ == '__main__':
#     app = wx.App()
#     metadata_panel = MetadataPanel(None)
#     metadata_panel.show()
#     app.MainLoop()