# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import time
from psychopy import core, visual, event
import pandas as pd
import random
from pathlib import Path
from typing import List, Tuple

from rcp_task_acquisition.tasks import bases
import rcp_task_acquisition.tasks.NBack.configs as cfg
from rcp_task_acquisition.utils.enums import Answer
from rcp_task_acquisition.utils.constants import CODE_DIR
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/NBack") 

LETTERS = ["D","F","H","J","K","L","M","S","T","V"]

"""
Select a sequence of stimuli file paths for presentation.

Rules:
- Stimuli live in ./resources/stimuli/ as attneave_1.png ... attneave_10.png.
- All public builders return List[Path] with length == trial_num, elements are absolute Paths.
- 1-back (pull_stimuli_1back):
    - Generates deterministic sequences with exactly 6 targets per block.
    - Ensures no more than 3 consecutive repetitions of the same stimulus.
    - Expected trials per block: 21 (14 non-targets + 6 targets + 1 for n-level).
- 2-back (pull_stimuli_2back):
    - Generates deterministic sequences with exactly 6 targets per block.
    - Ensures no more than 3 consecutive repetitions of the same stimulus.
    - Expected trials per block: 22 (14 non-targets + 6 targets + 2 for n-level).
- Logging: INFO when (re)setting targets; DEBUG for each trial's decision and chosen file name.
"""



# Parameters
PARAMS = {
    # "reps_per_trial":0, # Number of reps to do of all stimuli
    # "randomSeed":0 ,# Random seed
    # "nBackDegree" :1 ,# What is the N in N-Back?
    "ISITime": 2.5 ,# How long is ISI
    "stimTime" :0.5, # time stimulus is on in seconds,
    }
# basedir = "/home/rcp/task-acquisition/tasks"
imdir = os.path.join(CODE_DIR, "tasks", "NBack", "stimuli")
# nReps = 3 # Number of reps to do of all stimuli
# randomSeed = 0 # Random seed
# nBackDegree = 1 # What is the N in N-Back?
# ISITime = 2.5 # How long is ISI
# stimTime = 0.5 # time stimulus is on in seconds
matchKey = 'm'
# postStimBuffer = 0.1 # Time within stimulus to ignore keypresses
gClock = core.monotonicClock
one_back_instructions = "If the letter matches the previous letter"
two_back_instructions = "If the letter matches the letter shown 2 letters ago"
one_back_str = "1-back"
two_back_str = "2-back"
one_back_secondary_instructions = "If the letter is different from the letter shown 2 letters ago"
two_back_secondary_instructions = "If the letter is different from the letter shown 2 letters ago"




def _is_practice_block(trial_num: int) -> bool:
    """
    Determine if this is a practice block based on trial count.
    Practice blocks have 10 trials, experimental blocks have 21-23 trials.
    
    Args:
        trial_num: Number of trials in the block
        
    Returns:
        True if this is a practice block, False otherwise
    """
    return trial_num == 10


def _all_stimuli_paths() -> list[Path]:
    # """Return the list of all available stimuli paths (length = STIMULI_COUNT)."""
    # base = cfg.RESOURCES_DIR / "stimuli"
    # paths = [base / f"attneave_{i}.png" for i in range(1, cfg.STIMULI_COUNT + 1)]
    # missing = [p for p in paths if not p.exists()]
    # if missing:
    #     logger.error(f"Missing stimuli files: {', '.join(str(m) for m in missing)}")
    #     raise FileNotFoundError(f"Missing stimuli files: {', '.join(str(m) for m in missing)}")
    return LETTERS #paths


def _create_deterministic_sequence(n_back_level: int, total_trials: int) -> Tuple[List[Path], List[Answer]]:
    """
    Generate deterministic stimulus sequence with exact target count and repetition constraints.
    
    This function creates sequences that have exactly TARGETS_PER_BLOCK targets and ensures
    no stimulus repeats more than MAX_CONSECUTIVE_REPEATS times consecutively.
    
    Args:
        n_back_level: The n-back level (1, 2, or 3)
        total_trials: Total number of trials in the sequence
        
    Returns:
        Tuple containing stimulus paths and corresponding answer sequence
    """
    all_paths = _all_stimuli_paths()
    
    while True:  # Keep generating until valid sequence found
        # Step 1: Generate random sequence using available stimuli (1-10)
        sequence_numbers = [random.randint(1, cfg.STIMULI_COUNT) for _ in range(total_trials)]
        
        # Step 2: Identify targets automatically based on n-back rule
        target_count = 0
        target_positions = []
        
        for pos in range(n_back_level, len(sequence_numbers)):
            if sequence_numbers[pos] == sequence_numbers[pos - n_back_level]:
                target_count += 1
                target_positions.append(pos)
        # Step 3: Validate exact target count requirement
        if target_count != cfg.TARGETS_PER_BLOCK:
            continue  # Regenerate if wrong number of targets
            
        # Step 4: Validate consecutive repetition constraint
        has_too_many_repeats = False
        for i in range(len(sequence_numbers) - cfg.MAX_CONSECUTIVE_REPEATS):
            # Check if stimulus repeats more than allowed consecutive times
            consecutive_same = True
            for j in range(1, cfg.MAX_CONSECUTIVE_REPEATS + 1):
                if sequence_numbers[i] != sequence_numbers[i + j]:
                    consecutive_same = False
                    break
            if consecutive_same:
                has_too_many_repeats = True
                break
        if has_too_many_repeats:
            continue  # Regenerate if too many consecutive repeats
            
        # Step 5: Valid sequence found - convert to paths and generate answers
        stimulus_paths = [all_paths[num - 1] for num in sequence_numbers]  # Convert 1-based to 0-based indexing

        answers = []
        
        for pos in range(len(sequence_numbers)):
            if pos < n_back_level:
                answers.append(Answer.NOGO)  # First n positions cannot be evaluated
            elif pos in target_positions:
                answers.append(Answer.SAME)   # This is a target (match)
            else:
                answers.append(Answer.DIFFERENT)  # This is a non-target
        logger.info(f"Generated deterministic {n_back_level}-back sequence: {target_count} targets in {total_trials} trials")
        return stimulus_paths, answers


def _create_practice_sequence(n_back_level: int, total_trials: int) -> Tuple[List[Path], List[Answer]]:
    """
    Generate deterministic stimulus sequence for practice blocks with 3 targets.
    
    This function creates practice sequences that have exactly 3 targets and ensures
    no stimulus repeats more than MAX_CONSECUTIVE_REPEATS times consecutively.
    
    Args:
        n_back_level: The n-back level (1, 2, or 3)
        total_trials: Total number of trials in the sequence (typically 10)
        
    Returns:
        Tuple containing stimulus paths and corresponding answer sequence
    """
    all_paths = _all_stimuli_paths()
    
    while True:  # Keep generating until valid sequence found
        # Step 1: Generate random sequence using available stimuli (1-10)
        sequence_numbers = [random.randint(1, cfg.STIMULI_COUNT) for _ in range(total_trials)]
        
        # Step 2: Identify targets automatically based on n-back rule
        target_count = 0
        target_positions = []
        
        for pos in range(n_back_level, len(sequence_numbers)):
            if sequence_numbers[pos] == sequence_numbers[pos - n_back_level]:
                target_count += 1
                target_positions.append(pos)
        
        # Step 3: Validate exact target count requirement (3 for practice)
        if target_count != 3:
            continue  # Regenerate if wrong number of targets
            
        # Step 4: Validate consecutive repetition constraint
        has_too_many_repeats = False
        for i in range(len(sequence_numbers) - cfg.MAX_CONSECUTIVE_REPEATS):
            # Check if stimulus repeats more than allowed consecutive times
            consecutive_same = True
            for j in range(1, cfg.MAX_CONSECUTIVE_REPEATS + 1):
                if sequence_numbers[i] != sequence_numbers[i + j]:
                    consecutive_same = False
                    break
            if consecutive_same:
                has_too_many_repeats = True
                break
        
        if has_too_many_repeats:
            continue  # Regenerate if too many consecutive repeats
            
        # Step 5: Valid sequence found - convert to paths and generate answers
        stimulus_paths = [all_paths[num - 1] for num in sequence_numbers]  # Convert 1-based to 0-based indexing
        answers = []
        
        for pos in range(len(sequence_numbers)):
            if pos < n_back_level:
                answers.append(Answer.NOGO)  # First n positions cannot be evaluated
            elif pos in target_positions:
                answers.append(Answer.SAME)   # This is a target (match)
            else:
                answers.append(Answer.DIFFERENT)  # This is a non-target
                
        logger.info(f"Generated practice {n_back_level}-back sequence: {target_count} targets in {total_trials} trials")
        return stimulus_paths, answers


def pull_stimuli_1back(trial_num: int) -> Tuple[List[Path], List[Answer]]:
    """
    Generate deterministic stimulus sequence for 1-back tasks.
    
    Creates sequences with exactly TARGETS_PER_BLOCK targets for experimental blocks (21 trials)
    or 3 targets for practice blocks (10 trials), and validates that no stimulus repeats 
    more than MAX_CONSECUTIVE_REPEATS times consecutively.
    
    Args:
        trial_num: Number of trials to prepare
        
    Returns:
        Tuple containing stimulus paths and answer sequence
    """
    # Check if this is a practice block
    if _is_practice_block(trial_num):
        logger.info(f"Detected 1-back practice block with {trial_num} trials")
        return _create_practice_sequence(1, trial_num)
    
    # Regular experimental block
    expected_trials = cfg.NON_TARGETS_BASE + cfg.TARGETS_PER_BLOCK + 1  # 14 + 6 + 1 = 21
    
    if trial_num != expected_trials:
        logger.warning(f"1-back expects {expected_trials} trials, got {trial_num}. Using deterministic generation anyway.")
    
    return _create_deterministic_sequence(1, trial_num)


def pull_stimuli_2back(trial_num: int) -> Tuple[List[Path], List[Answer]]:
    """
    Generate deterministic stimulus sequence for 2-back tasks.
    
    Creates sequences with exactly TARGETS_PER_BLOCK targets for experimental blocks (22 trials)
    or 3 targets for practice blocks (10 trials), and validates that no stimulus repeats 
    more than MAX_CONSECUTIVE_REPEATS times consecutively.
    
    Args:
        trial_num: Number of trials to prepare
        
    Returns:
        Tuple containing stimulus paths and answer sequence
    """
    # Check if this is a practice block
    if _is_practice_block(trial_num):
        logger.info(f"Detected 2-back practice block with {trial_num} trials")
        return _create_practice_sequence(2, trial_num)
    
    # Regular experimental block
    expected_trials = cfg.NON_TARGETS_BASE + cfg.TARGETS_PER_BLOCK + 2  # 14 + 6 + 2 = 22
    
    if trial_num != expected_trials:
        logger.warning(f"2-back expects {expected_trials} trials, got {trial_num}. Using deterministic generation anyway.")
    
    return _create_deterministic_sequence(2, trial_num)


class N_back(bases.StimulusBase):
    def __init__(self, window, frame, button, is_finished):
        self.parameters = {}
        super().__init__(window, frame)
        self.button = button
        self.trial = 0
        self.is_real = None
        self.type = None
        self.button_press = False
        self.finished = is_finished
        self.instructions = None
        self.letters = {"D": visual.TextStim(self.display, text="D", name="trial", pos=(-100, 0), height=1000),
                        "F": visual.TextStim(self.display, text="F", name="trial", pos=(-50,  0), height=1000),
                        "H": visual.TextStim(self.display, text="H", name="trial", pos=(-100, 0), height=1000),
                        "J": visual.TextStim(self.display, text="J", name="trial", pos=(0,  150), height=1000),
                        "K": visual.TextStim(self.display, text="K", name="trial", pos=(-50,  0), height=1000),
                        "L": visual.TextStim(self.display, text="L", name="trial", pos=(-50,  0), height=1000),
                        "M": visual.TextStim(self.display, text="M", name="trial", pos=(-200, 0), height=1000),
                        "S": visual.TextStim(self.display, text="S", name="trial", pos=(-50,  0), height=1000),
                        "T": visual.TextStim(self.display, text="T", name="trial", pos=(-100, 0), height=1000),
                        "V": visual.TextStim(self.display, text="V", name="trial", pos=(-100, 0), height=1000)}
        
        
    #Sets up display window, fixation cross, text pages and image stimuli
    def setupWinStims(self, imdir):
        fixation = visual.TextStim(self.display, text="+", name="FixationCross", height=50)
        texts = []
        
        # Initialize the image stimuli
        ims = []
        picture_list = []
        correct_img = visual.ImageStim(self.display, image=os.path.join(imdir, cfg.CORRECT_IMG), name=cfg.CORRECT_IMG, size=[300, 300])
        incorrect_img = visual.ImageStim(self.display, image=os.path.join(imdir, cfg.INCORRECT_IMG), name=cfg.INCORRECT_IMG, size=[300, 300])
        logger.debug(f"ims: {correct_img}, {incorrect_img}")
        # for fi in os.listdir(imdir) :
        #     ims.append(visual.ImageStim(self.display, image=os.path.join(imdir, fi), name=fi, size=[300, 300]))
        #     picture_list.append(fi)
                
        self.metadata = picture_list
        return (fixation, texts, correct_img, incorrect_img)
    
    # Sets up trial data structure and stimuli presentation order
    def setupTrialData(self, nReps, ims, randomSeed, ISITime, stimTime, nBackDegree) :
        random.seed(0)
        nStim = len(ims)
        nTrials = nStim*nReps
        allStimIdx = list(range(1,nStim+1)) * nReps
        allStimIdxShuff = allStimIdx
        random.shuffle(allStimIdxShuff)
        stimImageNames = [None] * nTrials
        correctResponse = [None] * nTrials
        for stimi in range(nTrials) :
            stimImageNames[stimi] = ims[allStimIdxShuff[stimi]-1].name
            if stimi > nBackDegree-1 :
                if allStimIdxShuff[stimi] == allStimIdxShuff[stimi-nBackDegree] :
                    correctResponse[stimi] = matchKey
        tData = {'Trial_Num' : list(range(1,nTrials+1)),
                  'Stim_Image' : stimImageNames,
                  'Stim_Index' : allStimIdxShuff,
                  'Correct_Response' : correctResponse,
                  'Actual_Response' : [None] * nTrials,
                  'Was_Correct' : [None] * nTrials,
                  'Reaction_Time' : [None] * nTrials,
                  'Stimulus_Length_Nominal' : [stimTime] * nTrials,
                  'Stimulus_Length_Actual' : [None] * nTrials,
                  'ISI_Length_Nominal' : [ISITime] * nTrials,
                  'ISI_Length_Actual' : [None] * nTrials}
        trialData = pd.DataFrame(tData)
        return trialData
    
    # Show and log a stimulus
    def showAndLog(self, win, timeData, triali, stim, dur, name, draw_patch = False) :
        # stim.draw()
        # patch = draw_patch
        self.display.switch_patch()
        thisFlipTime, flip_diff = win.flip()
        timeData.loc[len(timeData)] = [name, triali, thisFlipTime]
        while gClock.getTime()-thisFlipTime < dur :
            
            stim.draw()
            if draw_patch:
                # self.display.switch_patch()
                self.display.draw_patch()
                # patch = False
            win.flip()
            if self.button.value:
                self.button_press = True
        self.display.switch_patch()
        return [ timeData, thisFlipTime]
            
    def present(self, test=True, getTime=False):
        # clear global event keys
        self.trial+=1

        self.instructions = cfg.ONE_BACK_DISPLAY if self.type == 1 else cfg.TWO_BACK_DISPLAY
        event.globalKeys.clear()
        end_text = visual.TextStim(self.display, text="Task Finished. Thank you.", name="Finish", height=50)
        logger.debug(self.type)
        logger.debug(self.is_real)
        # Initialize the display window
        fixation, texts, correct_ims, incorrect_ims = self.setupWinStims(imdir)
        # Set up a dataframe to hold time data
        timeDataColumns = ['Event_Name', 'Trial_Num', 'Time_Since_Start']
        timeData = pd.DataFrame(columns=timeDataColumns)
        fixation = visual.TextStim(self.display, text="+", name="FixationCross", pos=(0, 0), height=50)

        trial_list=[]
        answer_list = []
        intertrial_text =  self.intertrial_instructions()
        
        
        #show intro based on data:
        if self.is_real:
            text = self.real_instructions()
            for i in range(0,3):
                trials, answers =pull_stimuli_1back(21) if self.type == 1 else pull_stimuli_2back(22)
                trial_list.append(trials)
                answer_list.append(answers)
        else:
            text = self.practice_instructions()
            for i in range(0,2):
                trials, answers =pull_stimuli_1back(10) if self.type == 1 else pull_stimuli_2back(10)
                trial_list.append(trials)
                answer_list.append(answers)

        PARAMS[f"trial_{self.trial}"]  = {"trials": list(trial_list),
                                        "reps_per_trial":len(list(trial_list)),
                                        "n_back_type": self.type,
                                        "real": self.is_real}
        self.trial_list = trial_list
        for index, _ in enumerate(text):
            
            while not self.button.value:
                if self.finished.value == 2:
                    break
                text[index].draw()
                self.display.flip()
                # time.sleep(5)
                time.sleep(0.05)
            while self.button.value:
                time.sleep(0.05)
            if self.finished.value == 2:
                self.display.flip()
                self.is_real=None
                self.button_press = False
                return
        self.play_tone()
        core.wait(0.05)
        timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, fixation, PARAMS["ISITime"], "Initial_Fixation_Shown")
        # PARAMS[f"trial_{self.trial}"] = list(trial_list)


        for index, trial_set in enumerate(trial_list):
            for t_index, trial in enumerate(trial_set):
                if self.finished.value == 2:
                    self.display.flip()
                    self.is_real=None
                    self.button_press = False
                    return
                trial_vis = self.letters[trial]
                self.button_press = False
                timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, trial_vis, PARAMS["stimTime"], "Trial_Shown", True) 
                timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, fixation, PARAMS["ISITime"], "Initial_Fixation_Shown")
                if not self.is_real:
                    if self.button.value:
                        self.button_press
                    if self.button_press:
                        if answer_list[index][t_index] == Answer.DIFFERENT:
                            
                            timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, incorrect_ims, 2, "Initial_Fixation_Shown")
                        elif answer_list[index][t_index] == Answer.SAME or answer_list[index][t_index] == Answer.NOGO:
                            timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, correct_ims, 2, "Initial_Fixation_Shown")
                    elif answer_list[index][t_index] == Answer.DIFFERENT or answer_list[index][t_index] == Answer.NOGO:
                            timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, correct_ims, 2, "Initial_Fixation_Shown")
                    elif answer_list[index][t_index] == Answer.SAME:
                        timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, incorrect_ims, 2, "Initial_Fixation_Shown")
                    self.button_press = False
            if index < len(trial_list)-1:
                if self.finished.value == 2:
                    self.display.flip()
                    self.is_real=None
                    self.button_press = False
                    return

                timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, intertrial_text[0], 10, "intertrial_text")
                
                self.play_tone()
                core.wait(0.05)
                timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, fixation, PARAMS["ISITime"], "Initial_Fixation_Shown")

            
        timeData, fixFlipTime =self.showAndLog(self.display, timeData, 0, end_text, 2, "Trial_Shown") 
        self.is_real=None
        self.button_press = False
        logger.debug(f"RUN PARAMS: {PARAMS}")
        

    def saveMetadata(self, name, sessionFolder):
        logger.debug(f"PARAMS: {PARAMS}")
        return PARAMS

        
    def update_data(self, selections):
        self.is_real = True if selections[0] == "real" else False
        self.type = 1 if selections[1] == "1-back" else 2
        
        # PARAMS["n_back_type"] = self.type
        # PARAMS["real"] = self.is_real
         
    
    def intertrial_instructions(self):
        texts = []
        string = ("You will now have a 10 second break.\n"\
                  f"Remember: If the letter matches the {self.instructions['instruction']}, press the button.\n" \
                  "If the letter is different, do nothing.\n"\
                  "Respond as quickly and accurately as possible.\n")
        texts.append(visual.TextStim(self.display, 
                                     text=string, 
                                     name="intertrial_instructions", 
                                     wrapWidth=1000, 
                                     height=50))
        return texts


    def practice_instructions(self):
        texts = []
        str_list = []
        label = "practice_welcome"
        str_list.append(f"This is the {self.instructions['name']} practice task.\n"\
                  f"If the letter matches the {self.instructions['instruction']}, press the button.\n"\
                   "If the letter is different, do nothing.\n"\
                   "For each letter, you must decide if it matches the target letter.\n"\
                   "Press the button to advance.")
        str_list.append("We are measuring your speed, so respond as quickly as possible.\n"\
                  "Keep your index finger on the button, so you are always ready.\n"\
                  "Please use whichever hand you are more comfortable using.\n"\
                  "Press the button to advance")
        str_list.append("You will complete several practice trials.\n" \
                  "After each trial you will see if you were correct, incorrect or too slow.\n"\
                  "You will have a limited time to respond to each letter.\n"\
                  "Respond as quickly and accurately as possible.\n" \
                  "Press the button to advance.") 
        str_list.append(f"Remember: If the letter matches the {self.instructions['instruction']}, press the button.\n" \
              "If the letter is different, do nothing.\n"\
              "Respond as quickly and accurately as possible\n" \
              "Press the button to begin the practice trials")
        for string in str_list:
            texts.append(visual.TextStim(self.display, 
                                         text=string,
                                         name=label, 
                                         wrapWidth=1000, 
                                         height=50))
        return texts


    def real_instructions(self):
        texts = []
        str_list = []
        label = "task_instructions"
        str_list.append(f"You will now begin the {self.instructions['name']} task which will last about 3 minutes.\n"\
                        "You will not recieve feedback.\n"\
                        "Respond as quickly and accurately as possible.\n"\
                        "Press the button to advance.")
        str_list.append(f"Remember: If the letter matches the {self.instructions['instruction']}, press the button.\n" \
                        "If the letter is different, do nothing.\n"\
                        "Respond as quickly and accurately as possible.\n" \
                        "Press the button to begin the trials ")
        for string in str_list:
            texts.append(visual.TextStim(self.display, 
                                         text=string, 
                                         name=label, 
                                         wrapWidth=1000, 
                                         height=50))
            
        return texts


    def finish(self):
        label = "end_text"
        return visual.TextStim(self.display, 
                               text=("Task complete"\
                                     "\nThank you for participating!"), 
                               name=label, 
                               wrapWidth=1000, 
                               height=50)