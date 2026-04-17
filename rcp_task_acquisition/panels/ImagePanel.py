import wx
import wx.lib.dialogs
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/ImagePanel") 


class ImagePanel(wx.Panel):
    def __init__(self, parent, **kwargs):

        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
        self.figure = Figure()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        

    def updateImage(self,  gui_size, **kwargs):
        '''
        Switching to a toggle method so there will always be only 2 cameras at a time
        '''
        column_count = 2
        row_pos = 0.005
        row_inc = 0.5
        self.figure.clf() 
        self.axes = list()
        self.figure.patch.set_facecolor('none')
        props = dict(boxstyle='square', facecolor=(0.8, 0.8, 0.8), edgecolor=(0.1, 0.1, 0.1), alpha=0.75)
        for c in range(int(column_count)):
            self.axes.append(self.figure.add_subplot(1, column_count, c+1, frameon=True))
            
            self.axes[c].set_position([row_pos, 0.005, 0.49, 0.99])
            
            row_pos += row_inc
            self.axes[c].xaxis.set_visible(False)
            self.axes[c].yaxis.set_visible(False)
        self.texts = []
        for index, axis in enumerate(self.axes):
            self.texts.append(axis.text(5, 5, str(index),  fontsize=8, color=(0.9,0.9,0.9),
                            verticalalignment='top', bbox=props))
        self.canvas.draw()
        self.Refresh()
        self.Update()
        
        
    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figure,self.axes,self.canvas)


    def update_names(self, cam_name_list):
        for index, axis in enumerate(self.axes):
            self.texts[index].remove()
            props = dict(boxstyle='square', facecolor=(0.1, 0.1, 0.1), edgecolor=(0.1, 0.1, 0.1), alpha=0.75)
            self.texts[index] = axis.text(5, 5, cam_name_list[index],  fontsize=8, color=(0.9,0.9,0.9),
                            verticalalignment='top', bbox=props)
        self.canvas.draw()
        self.Refresh()
        self.Update()
    
    
    def draw(self):
        self.figure.canvas.draw()
    
    def reset_sizing(self):
        self.canvas.ClearBackground()
        self.canvas.draw()
        self.Refresh()
        self.Update()