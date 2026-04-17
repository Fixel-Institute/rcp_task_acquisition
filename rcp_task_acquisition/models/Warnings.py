import wx

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/LabjackFrontend") 

class Warning():
    def __init__(self, error_type=None, info=None):
        self.msg = self._get_error(error_type, info)
        self.has_warned = False

    
    def display(self):
        logger.debug(self.msg)
        warning_box = wx.MessageDialog(parent=None, 
                                       message=self.msg, 
                                       caption="Warning!", 
                                       style=wx.OK|wx.ICON_EXCLAMATION)
        warning_box.ShowModal()
        warning_box.Destroy()
        self.has_warned = True
    
    def update_error(self, error, info=None):
        self.msg = self._get_error(error, info)
        self.has_warned = False
    
    def _get_error(self, error, info=None):
        if error=="labjack":
            return "Error loading labjack, please check that the labjack is plugged in."
        elif error=="camera":
            return "Error loading cameras, please check that both cameras are plugged in and restart the program."
        elif error=="projector":
            return "Second monitor is not being recognized. Please make sure there are 2 monitors available."
        elif error=="stim_time":
            return "Error in Calculating stimulus timing. We are unsure of the disk space that will be taken up and cannot guarantee that there will be sufficient space."
        elif error=="space":
            return "There is not enough disk space for the requested duration."
        elif error == "compression":
            return "Cannot close until previous compression completes!"
        elif error == "frames":
            return f"Warning! {info}."
        elif error == "display":
            return "Please make sure both monitors are installed."
        elif error == "hardware":
            return "Please select labjack connections before continuing."
        elif error == "no_hardware":
            return "Please set up hardware before continuing."
        elif error == "name":
            return "Please put a name in user input."
        elif error == "serial":
            return "Please add a serial number before continuing."
        elif error == "compress":
            "Please DO NOT close this GUI until compression is complete!!!"
        elif error == "frames":
            f"Warning! {info}"
        else:
            return None
        
    def get_has_warned(self):
        return self.has_warned