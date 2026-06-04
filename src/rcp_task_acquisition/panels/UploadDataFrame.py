import os
import wx
import threading

from rcp_task_acquisition.utils import file_utils
from rcp_task_acquisition.utils.bravo_uploader import uploadRCPSession

class UploadDataFrame(wx.Frame):
    def __init__(self, parent):
        super(UploadDataFrame, self).__init__(parent, title="Data Upload Panel", size=(800, 500))
        self.panel = DirectoryLookupPanel(self)
        self.Show()

class DirectoryLookupPanel(wx.Panel):
    def __init__(self, parent):
        super(DirectoryLookupPanel, self).__init__(parent)
        
        self.user_cfg = file_utils.read_config('userdata.yaml')
        self.root_directory = self.user_cfg.get('RawDataDir', "")
        self.subdirectories = []
        self.upload_directory = ""

        self.layout = wx.BoxSizer(wx.VERTICAL)

        # Root directory input
        self.root_dir_label = wx.StaticText(self, label="Root Directory:")
        self.root_dir_input = wx.TextCtrl(self)
        self.root_dir_input.Bind(wx.EVT_TEXT, self.on_root_dir_change)
        self.root_dir_input.Enable(False)  # Disable manual input, only allow browsing

        #self.browse_button = wx.Button(self, label="Browse")
        self.layout.Add(self.root_dir_label, 0, wx.ALL, 5)
        self.layout.Add(self.root_dir_input, 0, wx.ALL | wx.EXPAND, 5)
        #self.layout.Add(self.browse_button, 0, wx.ALL, 5)
        
        # Subdirectory list
        self.subdir_label = wx.StaticText(self, label="Subdirectories:")
        self.subdir_listbox = wx.ListBox(self)
        self.subdir_listbox.Bind(wx.EVT_LISTBOX, self.on_subdir_select)
        
        self.layout.Add(self.subdir_label, 0, wx.ALL, 5)
        self.layout.Add(self.subdir_listbox, 1, wx.ALL | wx.EXPAND, 5)

        self.upload_button = wx.Button(self, label="Upload Data")
        self.upload_button.Bind(wx.EVT_BUTTON, self.on_upload)
        self.layout.Add(self.upload_button, 0, wx.ALL, 5)
        
        self.root_dir_input.SetValue(self.root_directory)

        self.SetSizer(self.layout)

        self.overlay = wx.Overlay()
        self.spinner = wx.ActivityIndicator(self)
        self.spinner.Hide()  # Hide it initially

    def on_root_dir_change(self, event):
        new_root = self.root_dir_input.GetValue()
        if new_root.endswith(os.path.sep):
            new_root = new_root[:-1]
        self.root_directory = new_root
        self.subdirectories = []
        self.update_subdirectories()
    
    def on_subdir_select(self, event):
        selected_index = self.subdir_listbox.GetSelection()
        if selected_index != wx.NOT_FOUND:
            selected_subdir = self.subdir_listbox.GetString(selected_index)
            if selected_subdir == ".." :
                if len(self.subdirectories) > 0:
                    self.subdirectories.pop()
                    self.update_subdirectories()
            else: 
                if len(self.subdirectories) == 0 or not selected_subdir == self.subdirectories[-1]:
                    has_session_file = False
                    subpath = os.path.sep.join(self.subdirectories)
                    for item in os.listdir(os.path.join(self.root_directory, subpath, selected_subdir)):
                        if item.endswith(".yaml"):
                            has_session_file = True
                            break

                    if not has_session_file:
                        self.subdirectories.append(selected_subdir)
                        self.update_subdirectories()
                    else:
                        self.upload_directory = os.path.join(self.root_directory, subpath, selected_subdir)
    
    def update_subdirectories(self):
        subpath = os.path.sep.join(self.subdirectories)
        available_subdirs = os.listdir(self.root_directory + os.path.sep + subpath)
        
        self.subdir_listbox.Clear()
        self.subdir_listbox.Append("..")
        for subdir in available_subdirs:
            if os.path.isdir(os.path.join(self.root_directory, subpath, subdir)):
                self.subdir_listbox.Append(subdir)
    
    def on_upload(self, event):
        if self.upload_directory:
            wx.MessageBox(f"Uploading data from: {self.upload_directory}", "Upload", wx.OK | wx.ICON_INFORMATION)

            self.uploading_worker_thread = threading.Thread(target=uploadRCPSession, args=(self.upload_directory, self.upload_directory.replace(self.root_directory + os.path.sep, "").replace(os.path.sep, "_"),
                                                                                           self.on_upload_complete, self.on_upload_error), daemon=True)
            self.uploading_worker_thread.start()
            self.upload_button.Enable(False)
            self.subdir_listbox.Enable(False)

            panel_size = self.GetSize()
            spinner_size = self.spinner.GetSize()
            x = (panel_size.width - spinner_size.width) // 2
            y = (panel_size.height - spinner_size.height) // 2
            self.spinner.SetPosition(wx.Point(x, y))
            self.spinner.Show()
            self.spinner.Start()

        else:
            wx.MessageBox("Please select a valid directory to upload.", "Error", wx.OK | wx.ICON_ERROR)

    def on_upload_error(self, error_message):
        wx.MessageBox(f"Upload failed: {error_message}", "Error", wx.OK | wx.ICON_ERROR)
        self.upload_button.Enable(True)
        self.subdir_listbox.Enable(True)

        self.spinner.Stop()
        self.spinner.Hide()
        self.overlay.Reset()  # Clear the overlay
        self.Refresh()

    def on_upload_complete(self, result):
        wx.MessageBox(f"Upload complete: {result}", "Success", wx.OK | wx.ICON_INFORMATION)
        self.upload_button.Enable(True)
        self.subdir_listbox.Enable(True)

        self.spinner.Stop()
        self.spinner.Hide()
        self.overlay.Reset()  # Clear the overlay
        self.Refresh()