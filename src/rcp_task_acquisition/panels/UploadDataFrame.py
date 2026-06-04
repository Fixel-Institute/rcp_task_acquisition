import os
import wx
import numpy as np 
import time
from collections import deque

class UploadDataFrame(wx.Frame):
    def __init__(self, parent):
        super(UploadDataFrame, self).__init__(parent, title="Data Upload Panel", size=(800, 500))
        self.panel = DirectoryLookupPanel(self)
        self.Show()

class DirectoryLookupPanel(wx.Panel):
    def __init__(self, parent):
        super(DirectoryLookupPanel, self).__init__(parent)
        
        self.root_directory = "/Users/jcagle/Documents/Github/rcp_task_acquisition/Data"
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
                    has_more_level = False
                    subpath = os.path.sep.join(self.subdirectories)
                    for item in os.listdir(os.path.join(self.root_directory, subpath, selected_subdir)):
                        if os.path.isdir(os.path.join(self.root_directory, subpath, selected_subdir, item)):
                            has_more_level = True
                            break

                    if has_more_level:
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
            # TODO: I was writing this at home so I don't have a good way to test yet. 
        else:
            wx.MessageBox("Please select a valid directory to upload.", "Error", wx.OK | wx.ICON_ERROR)