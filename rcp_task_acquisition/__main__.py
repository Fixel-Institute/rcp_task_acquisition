# -*- coding: utf-8 -*-
import wx
#set up matplotlib to be compatible on commandline/spyder
import matplotlib
matplotlib.use("qtagg")

from rcp_task_acquisition.panels.SwitchPanel import SwitchPanel



def run_app():
    app = wx.App()
    SwitchPanel()
    app.MainLoop()


if __name__ == '__main__': 
    run_app()

 