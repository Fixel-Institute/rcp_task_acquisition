# Screen on off for testing photodetector

# imports
import numpy as np
from psychopy import core, event, visual

from . import bases

# Parameters
nslow = 3
nfast = 5


# Sets up display window, fixation cross, text pages and image stimuli
class Photo_Test(bases.StimulusBase):
    def __init__(self, window, frame):
        super().__init__(window, frame)

    def present(self, test=True):
        # Initialize the image stimuli
        ims = []
        ims.append(
            visual.Circle(
                self.display,
                radius=300,
                pos=(-855, 495),
                units="pix",
                lineWidth=1,
                fillColor="white",
                colorSpace="rgb",
            )
        )
        ims.append(
            visual.Rect(
                self.display,
                width=1920,
                height=1200,
                lineWidth=0,
                fillColor="black",
                colorSpace="rgb",
            )
        )

        # MAIN
        # clear global event keys
        event.globalKeys.clear()
        # define quit key
        # event.globalKeys.add(key='q', func=core.quit, name="shutdown")

        # shorter name for the global clock
        gClock = core.monotonicClock

        # Initialize the display self.displaydow

        showTime = gClock.getTime()

        while gClock.getTime() - showTime < 2 * nslow:
            drawi = int(np.mod(np.floor(gClock.getTime() - showTime), 2))
            ims[drawi].draw()
            self.display.flip()

        for i in range(2 * nfast):
            drawi = int(np.mod(i, 2))
            ims[drawi].draw()
            self.display.flip()
