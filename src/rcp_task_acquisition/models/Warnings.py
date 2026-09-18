import enum
from typing_extensions import Self

import wx

from rcp_task_acquisition.utils.logger import get_logger

logger = get_logger("./models/LabjackFrontend")


class WarnCat(str, enum.Enum):
    LABJACK = "Error loading labjack, please check that the labjack is plugged in."

    CAMERA = "Error loading cameras, please check that both cameras are plugged in and restart the program."

    PROJECTOR = (
        "Second monitor is not being recognized. Please make sure there are 2 monitors available."
    )

    STIM_TIME = "Error in Calculating stimulus timing. We are unsure of the disk space that will be taken up and cannot guarantee that there will be sufficient space."

    SPACE = "There is not enough disk space for the requested duration."

    COMPRESSION = "Cannot close until previous compression completes!"

    FRAMES = r"Warning! {info}."

    DISPLAY = "Please make sure both monitors are installed."

    HARDWARE = "Please select labjack connections before continuing."

    NO_HARDWARE = "Please set up hardware before continuing."

    NAME = "Please put a name in user input."

    SERIAL = "Please add a serial number before continuing."

    COMPRESS = "Please DO NOT close this GUI until compression is complete!!!"

    VIDEO = "Video not found in current path"

    FPS = r"Warning! {info}"


class WarningHandler:
    def __init__(self, error_type: WarnCat | None = None, info: str | None = None):
        self.msg = "NA" if error_type is None else self._get_error(error_type, info)

    def display(self):
        logger.debug(self.msg)
        warning_box = wx.MessageDialog(
            parent=None, message=self.msg, caption="Warning!", style=wx.OK | wx.ICON_EXCLAMATION
        )
        warning_box.ShowModal()
        warning_box.Destroy()

    def update_error(self, error: WarnCat, info: str | None = None) -> Self:
        self.msg = self._get_error(error, info)
        return self

    @staticmethod
    def _get_error(error: WarnCat, info: str | None = None):
        err_v = error.value  # ensure gets the value
        msg = err_v if error is None else err_v.format(info=info)
        return msg
