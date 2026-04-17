import time
import numpy as np
from psychopy.visual import Window
from psychopy.visual import GratingStim

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./utils/displays") 


_lowStateTexture = np.full([16, 16], -1).astype(np.int8)
_highStateTexture = np.full([16, 16], 1).astype(np.int8)


class Window(Window):
    """
    """
    # patchCoords=(600, -325, 200),
    def __init__(
        self,
        size=(1280, 1080),
        fov=(180, 100),
        fps=60,
        screen=1,
        color=-1,
        fullScreen=False, #-900
        patchCoords=(-850, 530, 150),
        textureShape=(16, 16)
        ):
        """
        """
        self.t = 0
        self.stimulus_frame = 0 
        self._countdown = None
        self._width, self._height = size
        self._azimuth, self._elevation = fov
        self._fps = fps
        self._ppd = self._width / self._azimuth
        self._textureShape = textureShape
        self._mc = None
        self._pulsing = False 
        self._stream = None
        super().__init__(
            size=(self.width, self.height),
            screen=screen,
            units='pix',
            gammaErrorPolicy='warn',
            useFBO=True,
            color=-1,
            # checkTiming=False,
            fullscr=fullScreen,
            waitBlanking=True,
            winType="pyglet"
        )
        self._state = False
        self._patchCoords = patchCoords
        x, y, s = self._patchCoords
        self._patch_is_light = False
        self._patch = GratingStim(
            self,
            tex=_highStateTexture,
            size=(s, s),
            pos=(x,y),
            units='pix'
        )
        self._backgroundColor = color
        self._background = GratingStim(
            self,
            tex=_lowStateTexture,
            size=(self.width, self.height),
            units='pix'
        )
        self._background.draw()
        # self._patch.draw()
        self.flip()
        return
    
    def switch_patch(self):
        self._patch_is_light = not self._patch_is_light
        self._patch.tex = _highStateTexture if self._patch_is_light else _lowStateTexture    
        
    def draw_patch(self):
        self._patch.draw()


    def pulse_patch(self, pulse_num, signal_length=1/30):
        count = 0
        while count < pulse_num:
            logger.debug(pulse_num)
            self._patch.tex = _highStateTexture
            self.signal_patch(signal_length)
            self._patch.tex = _lowStateTexture 
            self.signal_patch(signal_length)
            count+=1
        time.sleep(signal_length)
            
    def signal_patch(self, length):
        self.draw_patch()
        self.flip()
        time.sleep(length)
        
        
    def flip(self, prev_time=None, **kwargs):
        """
        # """
        # self.winHandle.maximize()
        # self.fullscr = True
        # self.winHandle.activate()
        
        
        
        # Write the current frame
        if self._stream is not None:
            frame = self.getNumpyArray()
            self._stream.write(frame)
    
        # self._patch_is_light = not self._patch_is_light
        flip_time =super().flip(**kwargs)
        flip_diff = (flip_time-prev_time) if prev_time != None else -1
        self.stimulus_frame +=1
        return flip_time, flip_diff
    

    def idle(self, duration=1, prev_time=None, time_list=None, units='seconds', returnFirstTimestamp=False):
        """
        """
        if units == 'frames':
            frameCount = int(duration)
        elif units == 'seconds':
            frameCount = round(self.fps * duration)

        for frameIndex in range(frameCount):
            self._background.draw()

            prev_time, time_diff = self.flip(prev_time)
            if time_list is not None and self.stimulus_frame <= len(time_list):
                time_list[self.stimulus_frame-1]  = time_diff
            if frameIndex == 0:
                 timestamp = prev_time

        return timestamp, time_list, prev_time


    def signalEvent(self, duration=3, units='frames', mc=False):
        """
        Flash the visual patch for a specific amount of time

        keywords
        --------
        duration: int of float
            Duration of the signalling event
        units: str
            Unit of time (frames or seconds)
        """

        #
        self._patch.tex = _highStateTexture
        self._state = True
        if units == 'frames':
            self._countdown = int(duration)
        elif units == 'seconds':
            self._countdown = round(self.fps * duration)
        else:
            raise Exception(f'{units} is an invalid unit of time')

        #
        if mc == True and self._mc is not None:
            self.callOnFlip(self._mc.signal)
            # self._mc.signal()

        return

    def clearStimuli(self):
        """
        """

        self._background.draw()
        timestamp = self.flip()

        return timestamp

    def drawBackground(self):
        self._background.draw()


    def close(self):
        super().close()


    def getNumpyArray(self, buffer='back', thumbnailSize=None):
        shape = (thumbnailSize, thumbnailSize)
        image = self.getMovieFrame(buffer=buffer)
        self.movieFrames = list()
        if thumbnailSize is not None:
            image.thumbnail(shape)
        array = np.array(image)

        return array

    
    def reset_stimulus_frame(self):
        self.stimulus_frame = 0

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def azimuth(self):
        return self._azimuth

    @property
    def elevation(self):
        return self._elevation

    @property
    def fps(self):
        return self._fps

    @property
    def ppd(self):
        return self._ppd

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        """
        """

        if value not in [True, False]:
            raise Exception(f'Invalid state: {value}')
        if value:
            self._patch.tex = _highStateTexture
        else:
            self._patch.tex = _lowStateTexture
        self._state = True if value else False

        return

    @property
    def patchCoords(self):
        return np.concatenate([self._patch.pos, self._patch.size])

    @patchCoords.setter
    def patchCoords(self, coords):
        x, y, w, h = coords
        self._patch.pos = (x, y)
        self._patch.size = (w, h)
        self._background.draw()
        self.flip()

    @property
    def backgroundColor(self):
        return self._backgroundColor

    @backgroundColor.setter
    def backgroundColor(self, color):
        if color < -1 or color > 1:
            raise Exception('Background color must be in the range (-1, 1)')
        self._background.tex = np.full(self._textureShape, color)
        self._backgroundColor = color
        self._background.draw()
        self.flip()

    def setBackgroundColor(self, color):
        """
        """
        if color < -1 or color > 1:
            raise Exception('Background color must be in the range (-1, 1)')
        self._background.tex = np.full(self._textureShape, color)
        self._backgroundColor = color
        return

