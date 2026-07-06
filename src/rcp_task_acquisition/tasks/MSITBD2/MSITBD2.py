import os
from pathlib import Path
import time
from PIL import Image

from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/MSITBD2") 

from psychopy import visual
from psychopy.hardware import keyboard
import pandas as pd

resource_path = Path(__file__).parent.__str__() + "/STIMULI"

# Sets up display window, fixation cross, text pages and image stimuli
class MSITBD2(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame, None, finish)
        self.trial = 0
        self.screen_width = 2200 #not technically screen width but we dont want to cover the photodiode
        self.screen_height = 1440

        self.trial_type = "Saccade"
        self.trial_data = []
        self.result_data = []

        self.kb = keyboard.Keyboard()
    
    def present_prep(self):
        self.trial_setup = pd.read_csv(Path(__file__).parent / "TrialList_Version1.csv")
        self.trial_setup["ImagePath"] = ""
        images = os.listdir(resource_path)
        self.trial_data = []
        self.result_data = []
        for index, row in self.trial_setup.iterrows():
            image_stim_path = ""
            image_path = ""
            for image in images:
                if image.startswith(str(row['Image']) + "."):
                    image_path = resource_path + "/" + image
                elif image.startswith(str(row['ImageStimulus']) + "."):
                    image_stim_path = resource_path + "/" + image

            with Image.open(image_path) as img:
                width, height = img.size
            new_height = (self.screen_width/width)*height
            new_width = self.screen_width
            if new_height > self.screen_height:
                new_width = (self.screen_height/height)*width
                new_height = self.screen_height
            stim = visual.ImageStim(self.display, image=image_path, name=row["Image"], size=[new_width, new_height], units='pix')

            if row["Stimuli"] == 0:
                keystim = stim
            else:
                if not image_stim_path:
                    keystim = stim
                else:
                    with Image.open(image_stim_path) as img:
                        width, height = img.size
                    new_height = (self.screen_width/width)*height
                    new_width = self.screen_width
                    if new_height > self.screen_height:
                        new_width = (self.screen_height/height)*width
                        new_height = self.screen_height
                    keystim = visual.ImageStim(self.display, image=image_stim_path, name=row["ImageStimulus"], size=[new_width, new_height], units='pix')

            self.trial_data.append({
                "Trial": index + 1,
                "Image": row['Image'],
                "ImagePath": image_path,
                "Jitter": row['Jitter'],
                "Stim": stim,
                "KeyStim": keystim
            })
            
    def present(self, test=True):
        self.play_tone()
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        #switch the photodiode patch to be "On" while the photo is being shown

        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()
            keys = self.kb.getKeys()
            to_start = False
            for key in keys:
                if key.name == "space":
                    to_start = True

            if to_start:
                break

        while self.finish.value == 0:
            for index in range(len(self.trial_data)):
                stim = self.trial_data[index]["Stim"]
                stim.draw()
                self.display.switch_patch()
                self.display.draw_patch()
                self.display.flip()

                print(f"Trial {index+1}: {self.trial_data[index]['Image']}")

                time.sleep(0.3)

                stim = self.trial_data[index]["KeyStim"]
                self.display.switch_patch()

                self.kb.clearEvents()
                start_time = time.time()
                now = time.time()
                while now - start_time < 1.7:
                    stim.draw()
                    self.display.draw_patch()
                    self.display.flip()

                    keys = self.kb.getKeys()
                    key_get = False
                    for key in keys:
                        if key.name == "left":
                            self.result_data.append({
                                "Trial": self.trial_data[index]["Trial"],
                                "Image": self.trial_data[index]["Image"],
                                "Response": "Left",
                                "RT": time.time() - start_time
                            })
                            print(f"Trial {index+1}: {self.trial_data[index]['Image']} - Response: Left, RT: {time.time() - start_time}")
                            key_get = True
                        elif key.name == "right":
                            self.result_data.append({
                                "Trial": self.trial_data[index]["Trial"],
                                "Image": self.trial_data[index]["Image"],
                                "Response": "Right",
                                "RT": time.time() - start_time
                            })
                            print(f"Trial {index+1}: {self.trial_data[index]['Image']} - Response: Right, RT: {time.time() - start_time}")
                            key_get = True
                        elif key.name == "down":
                            self.result_data.append({
                                "Trial": self.trial_data[index]["Trial"],
                                "Image": self.trial_data[index]["Image"],
                                "Response": "Down",
                                "RT": time.time() - start_time
                            })
                            print(f"Trial {index+1}: {self.trial_data[index]['Image']} - Response: Down, RT: {time.time() - start_time}")
                            key_get = True

                    if key_get:
                        break
                    
                    now = time.time()
                
                if len(self.result_data) < index + 1:
                    self.result_data.append({
                        "Trial": self.trial_data[index]["Trial"],
                        "Image": self.trial_data[index]["Image"],
                        "Response": "No Response",
                        "RT": -1
                    })
                    print(f"Trial {index+1}: {self.trial_data[index]['Image']} - Response: No Response, RT: {time.time() - start_time}")

                stim = self.trial_data[0]["Stim"]
                stim.draw()
                self.display.switch_patch()
                self.display.draw_patch()
                self.display.flip() 

                wait = max(0, self.trial_data[index]["Jitter"]/1000 - 1)   # jitter time minus the 1 second, don't know why, not even the MATLAB code knows why
                time.sleep(wait/2)

                stim.draw()
                self.display.switch_patch()
                self.display.draw_patch()
                self.display.flip()
                time.sleep(wait/2)

                if self.finish.value != 0:
                    break

        #turn the patch to off and flip the display to black
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        self.play_tone()
        
    def saveMetadata(self, name, sessionFolder):
        return {
            "task": name,
            "trial_data": [{
                "Trial": trial["Trial"],
                "Image": trial["Image"],
                "Jitter": trial["Jitter"]
            } for trial in self.trial_data],
            "result_data": [{
                "Trial": trial["Trial"],
                "Image": trial["Image"],
                "Response": trial["Response"],
                "RT": trial["RT"]
            } for trial in self.result_data]
        }
    
    def update_data(self, trial_data):
        self.trial_type = trial_data[1]