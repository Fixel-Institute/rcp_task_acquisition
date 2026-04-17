import os
import pathlib as pl
import numpy as np
import pandas as pd
import simpleaudio as sima
from psychopy import visual
from psychopy.visual.vlcmoviestim import VlcMovieStim

from rcp_task_acquisition.utils.constants import VIDEO_DIR, DURATION, FREQUENCY, SAMPLING_RATE
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/bases.py") 



class StimulusBase():
    """
    """

    def __init__(self, display, frame,  video_status=None, finish=None,):
        self.display = display
        self.frame = frame
        self.prev_flip_time = None
        self.metadata = None
        self.header = None
        self.total_time = None
        self.flip_interval_arr = None
        self.instructions_dict = {}
        self.current_trial = None
        self.video_status = video_status
        self.start_test = False
        self.finish = finish
        self.trial = 0
        return

    def present(self):
        
        self.trial+=1
        self.play_tone()
        #switch the photodiode patch to be "On" while the photo is being shown
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()

        while True:
            if self.finish.value == 2:
                break
        
        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.play_tone()
        
        pass
        
        
    def prepareMetadataStream(self, sessionFolder, filename, header):
        """
        """
        headerBreakLine = '-' * 40 + '\n'

        if self.metadata is None:
            return

        #
        sessionFolderPath = pl.Path(sessionFolder)
        if sessionFolderPath.exists() == False:
            sessionFolderPath.mkdir()

        #
        fullFilePath = sessionFolderPath.joinpath(f'{filename}.txt')

        #
        data = None
        if fullFilePath.exists():
            with open(fullFilePath, 'r') as stream:
                lines = stream.readlines()
            if len(lines) == 0:
                pass
            else:
                for lineIndex, line in enumerate(lines):
                    if line == headerBreakLine:
                        break
                data = lines[lineIndex + 1:]

        #
        stream = open(fullFilePath, 'w')
        for key, value in header.items():
            stream.write(f'{key}: {value}\n')
        stream.write(headerBreakLine)

        #
        if data is not None:
            for datum in data:
                stream.write(datum)

        return stream
    
    def get_time_diff_arr(self, total_time, fps):
        self.flip_interval_arr = np.zeros(int((total_time+5)*fps))
    
    def _time_flip(self):
        self.prev_flip_time, flip_int = self.display.flip(self.prev_flip_time)
        if self.flip_interval_arr is not None and self.display.stimulus_frame <= len(self.flip_interval_arr):
            self.flip_interval_arr[self.display.stimulus_frame-1] = flip_int 
        return self.prev_flip_time
    
    
    def _time_idle(self, duration=1, units='seconds', returnFirstTimestamp=False):
        timestamp, self.flip_interval_arr, self.prev_flip_time = self.display.idle(duration, 
                                                                                     self.prev_flip_time, 
                                                                                     self.flip_interval_arr, 
                                                                                     units,
                                                                                     returnFirstTimestamp)

        return timestamp
    
    def create_csv(self, name, sessionFolder, metadata, start_frame, columns=None):
        sessionFolderPath = pl.Path(sessionFolder)
        if sessionFolderPath.exists() == False:
            return
        csv_name = sessionFolderPath.joinpath(f"{name}-{int(start_frame)}.csv")

        data = pd.DataFrame(metadata)
        if columns: 
            data.columns = columns
        data.to_csv(csv_name, index=False)
    
    
    def set_first_frame(self, frame):
        self.first_frame = frame
        
        
    def saveMetadata(self, name, sessionFolder):
        if self.flip_interval_arr is not None:
            sessionFolderPath = pl.Path(sessionFolder)
            flip_updated = np.trim_zeros(self.flip_interval_arr, trim='b')
            if sessionFolderPath.exists() == False:
                return
            csv_name = sessionFolderPath.joinpath(f"{name}-{int(self.first_frame)}-flip_interval.csv")
            data = pd.DataFrame(flip_updated)
            data.to_csv(csv_name)
        
        
    def play_tone(self):
        # winsound.Beep(int(FREQUENCY), DURATION)
        self.play_stone(FREQUENCY, DURATION, SAMPLING_RATE)


    def reset_task(self):
        #placeholder
        pass
    
    def play_instructional_video(self, trial_name):
        if trial_name == "":
            file = self.instructions_dict
        else:
            file = self.instructions_dict[trial_name]
        path =  os.path.join(VIDEO_DIR, str(file))
        if not os.path.exists(path):
            raise RuntimeError(f"Video File could not be found: {path}")
        
        logger.debug(path)
        video = VlcMovieStim(
                self.display, 
                path,
                size=self.display.size,
                pos=[0, 0],     # Position the center of the video
                flipVert=False, 
                flipHoriz=False, 
                loop=False
            )
        logger.debug(video)
        video.play()
        while video.status != visual.FINISHED:
            if self.video_status.value == 2:
                video.pause()
                self.video_status.value = 0
            elif self.video_status.value == 3:
                video.play()
                self.video_status.value = 1
            elif self.video_status.value == 4:
                break                
            else:
                # Draw the current frame of the video
                video.draw()
                # Flip the window to show the new frame
                self.display.flip()

        video.stop()
        
        self.video_status.value = 5
        self.display.idle(time_list = [])
        # self.display.clearStimuli()


    def trial_bookends(self):
        '''
        could probably have a better name but I am tired today.
        this is the way most of the task start/end so it saves error by just combining
            them into the same function
        turn the photodiode patch on/off, draw, and play a tone.
        '''

        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()


    def update_data(self, data):
        pass
    
    def play_stone(self, frequency=440, duration=1.0, sample_rate=44100):
        """
        Generates and plays a sine wave tone.
        """
        try:
            # Generate time values
            t = np.linspace(0, duration, int(sample_rate * duration), False)
    
            # Generate sine wave
            tone = np.sin(frequency * t * 2 * np.pi)
    
            # Normalize to 16-bit range
            audio = (tone * 32767).astype(np.int16)
    
            # Play audio
            play_obj = sima.play_buffer(audio, 1, 2, sample_rate)
            play_obj.wait_done()
    
        except Exception as e:
            logger.error(f"Error generating tone: {e}")
