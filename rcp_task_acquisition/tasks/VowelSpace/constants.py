import os

from rcp_task_acquisition.utils.constants import CODE_DIR



PHRASE_LIST = ["hod", "heed", "who'd", "hoad"]

VS_NUM_TRIALS = 20

#volume for the .wav files since its softer than the start/end beeps
VOLUME = 0.7
STIM_DIR = os.path.join(CODE_DIR, "tasks/VowelSpace/stimuli")
VS_PATHS = {
    "hoad":  "say_hoad_again.wav",
    "heed":  "say_heed_again.wav",
    "who'd": "say_whod_again.wav",
    "hod":   "say_hod_again.wav"
    }

#paths for the instructional videos
VIDEO_PATHS = {
    "introduction": os.path.join("VowelSpaceArea", "VSA_instructions_captioned.mp4"),
    "hoad":  os.path.join("VowelSpaceArea", "say_hoad_again_vid.mp4"),
    "heed":  os.path.join("VowelSpaceArea", "say_heed_again_vid.mp4"),
    "who'd": os.path.join("VowelSpaceArea", "say_whod_again_vid.mp4"),
    "hod":   os.path.join("VowelSpaceArea", "say_hod_again_vid.mp4")
    }