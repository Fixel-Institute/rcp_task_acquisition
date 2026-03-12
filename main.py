# -*- coding: utf-8 -*-

import wx
from panels.SwitchPanel import SwitchPanel



if __name__ == '__main__':
    app = wx.App()
    main_panel = SwitchPanel()
    app.MainLoop()

