# -*- coding: utf-8 -*-
import time
import simpleaudio as sima
import numpy as np
from psychopy import visual

from rcp_task_acquisition.tasks import bases
from  rcp_task_acquisition.utils.constants import GLOBAL_CLOCK
from rcp_task_acquisition.tasks.ToneTaps.constants import TAP_DURATION, TAP_FREQUENCY, IVRY_TAPS_VIDEO_PATH 
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/ToneTaps") 



# Parameters
PARAMS = {
    "tone_number_per_trial": 12, # how many tones to play?
    "total_time_before_cutoff": 30, # how many seconds to run it after the tones stop
    "tone_hz":          TAP_FREQUENCY,
    "tone_duration":    TAP_DURATION,
    "inter_tone_interval":  0.5,
    "tone_delay":       1, # Seconds after start to begin tones
    "min_tap_interval": 0.05,
    "number_trials":    0,
    "hand_used": {}
    
    }



class ToneTapsClosed(bases.StimulusBase):
    def __init__(self, window, frame, press_count, finish, video_status):
        super().__init__(window, frame, video_status, finish)
        self.hand_list = []
        self.hand = None
        self.trial_count = 0
        self.first_tap = True
        self.press_count = press_count
        self.instructions_dict = IVRY_TAPS_VIDEO_PATH
        
    def present(self, test=True):
        # Initialize the message text
        texts = []
        texts.append(visual.TextStim(self.display, text="Tap in time with the tones.", name="WelcomeInstructions", height=50))
        texts.append(visual.TextStim(self.display, text="Keep tapping at the same rate.", name="End_Screen", height=50))
        texts.append(visual.TextStim(self.display, text="Thank you! Done", name="End_Screen", height=50))


        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        
        nPlayed = 0
        self.trial_count+=1
        PARAMS["hand_used"][f"trial_{self.trial_count}"] = self.hand
        self.play_tone()
        self.press_count.value = 0
        
        #start phase
        gToneTime = GLOBAL_CLOCK.getTime()
        playTime = PARAMS["tone_delay"]
        while self.press_count.value <= PARAMS["tone_number_per_trial"]-1:
            if GLOBAL_CLOCK.getTime() - gToneTime > playTime :

                # self.play_tone()
                self.play_tap()
                # self.stream.write(self.output_bytes)

                nPlayed+=1
                playTime += PARAMS["inter_tone_interval"]
            if self.finish.value == 2:
                break
        if self.press_count.value <= PARAMS["tone_number_per_trial"]:
            while True:
                if self.finish.value == 2:
                    break
                if GLOBAL_CLOCK.getTime() - gToneTime > playTime :
                    self.play_tap()

                    nPlayed+=1
                    playTime += PARAMS["inter_tone_interval"]
                    break
        if self.finish.value != 2: 
            texts[1].draw()
            self.display.draw_patch()
            self.display.flip()
        
        #continuation phase
        while (GLOBAL_CLOCK.getTime() - gToneTime) < (PARAMS["total_time_before_cutoff"]):
            if self.finish.value == 2:
                break
            time.sleep(0.005)
            if self.press_count.value >= 31 + PARAMS["tone_number_per_trial"]:
                break

           
        self.play_tone()     
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.first_tap = True

        
    def update_data(self, hand):
            self.hand = hand    
        
    def play_tap(self):
        t = np.linspace(0, TAP_DURATION, int(44100 * TAP_DURATION), False)

        # Generate sine wave
        sine_wave = np.sin(TAP_FREQUENCY * t * 2 * np.pi)
        # sine_wave = volume * np.sin(2 * np.pi * f * t)
    # Create a linear fade-in and fade-out with a flat middle

        taper_len = int(0.01 * len(sine_wave)) # 1% taper at each end
        
        taper = np.ones_like(sine_wave)
        
        taper[:taper_len] = np.linspace(0, 1, taper_len) # Fade in
        
        taper[-taper_len:] = np.linspace(1, 0, taper_len) # Fade out
        
        tapered_sine = sine_wave * taper

        audio = (tapered_sine * 32767).astype(np.int16)

        play_obj = sima.play_buffer(audio, 1, 2,44100)
        play_obj.wait_done()

        # Play using sounddevice
        # sd.play(tapered_sine, fs)
        
        
        
        
    def saveMetadata(self, name, sessionFolder):
        # sessionFolderPath = pl.Path(sessionFolder)
        # if sessionFolderPath.exists() == False:
        #     return
        
        # metadata = MetadataPanel()
        # if metadata.show() == wx.ID_OK:
        #     data = metadata.data
        #     data["parameters"] = PARAMS
        #     logger.debug(data)
        PARAMS["number_trials"] = self.trial_count

        return PARAMS
            
            