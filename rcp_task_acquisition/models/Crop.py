# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.patches as patches

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/Crop") 



class Crop():
    def __init__(self):
        self.croprec = list()
        self.croproi = list()  
        self.set_crop = None
    
    def set_key_crop(self, axes, keyCode):
        if self.cropAxes == None:
            return
        if keyCode == 314: #LEFT
            x = -1
            y = w = h =  0
        elif keyCode == 316: #RIGHT
            x = 1
            y = w = h = 0
        elif keyCode == 315: #UP
            x = w = h =  0
            y = -1
        elif keyCode == 317: #DOWN
            x = w = h = 0
            y = 1
        # Increase size
        elif keyCode == 65: #a
            x = -2
            y = +2
            w = h = +4
        # Decrease size
        elif keyCode == 83: #s
            x = +2
            y = -2
            w = h = -4

        ndx = axes.index(self.cropAxes)
        self.croproi[ndx][0] += x
        self.croproi[ndx][1] += w
        self.croproi[ndx][2] += y
        self.croproi[ndx][3] += h
       

            
    def create_crop(self, cam_cfg, cam_list, axes):
        ndx = axes.index(self.cropAxes)
        s = cam_list[ndx]
        cam_cfg[s]['crop'] = np.ndarray.tolist(self.croproi[ndx])
        
        
        
    def drawROI(self, axes):
        # if self.set_crop.GetValue():
        ndx = axes.index(self.cropAxes)
        self.croprec[ndx].set_x(self.croproi[ndx][0])
        self.croprec[ndx].set_y(self.croproi[ndx][2])
        self.croprec[ndx].set_width(self.croproi[ndx][1])
        self.croprec[ndx].set_height(self.croproi[ndx][3])
        if not self.croproi[ndx][0] == 0:
            self.croprec[ndx].set_alpha(0.6)
        # self.figure.canvas.draw()
        
        
    def adjust_crop(self, event, axes, cam_list, cam_config):
        self.cropAxes = event.inaxes
        ndx = axes.index(event.inaxes)
        s = cam_list[ndx]
        self.croproi[ndx] = cam_config[s]['crop']
        roi_x = event.xdata
        roi_y = event.ydata
        x_center = self.croproi[ndx][1]/2
        y_center = self.croproi[ndx][3]/2
        logger.info(f"x: {roi_x}, y: {roi_y}")
        logger.info(f"dimensions: {self.frmDims}")
        logger.info(f"center x = {x_center}, center y = {y_center}")
        if roi_x < x_center:
            roi_x = x_center
        elif roi_x+x_center > self.frmDims[3]:
            roi_x =  self.frmDims[3] - x_center
        if roi_y < y_center:
            roi_y = y_center
        if roi_y+y_center > self.frmDims[1]:
            roi_y = self.frmDims[1] - y_center
        self.croproi[ndx] = np.asarray([roi_x-self.croproi[ndx][1]/2,self.croproi[ndx][1],
                                        roi_y-self.croproi[ndx][3]/2,self.croproi[ndx][3]], int)
        logger.info(self.croproi)
        # self.drawROI()
         
        
    def update_crop(self, index, axis, frmDims):
        self.frmDims = frmDims
        cpt = self.croproi[index]
        rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.25,0.75], linewidth=2, linestyle='-',alpha=0.0)]
        self.croprec.append(axis.add_patch(rec[0]))

    
    def add_crop(self, crop):
        self.croproi.append(crop)