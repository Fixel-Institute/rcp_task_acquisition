# -*- coding: utf-8 -*-


# verbal fluency constants
TRIAL_TIME = 60
PHONEMIC_LIST = ['["F", "A", "S"]', '["C", "F", "L"]']
SEMANTIC_LIST = ["Animals", "Food and Drinks", "Fruits", "Tools"]
PHONEMIC_PHRASE = "Phonemic Fluency. Prompt the participant to say as many words beginning with the letter *"
SEMANTIC_PHRASE = "Semantic Fluency. Prompt the participant to say as many * as they can think of"
VERBAL_FLUENCY_PATHS = {
    "C.F.L": {
        "C": "VerbalFluency/VerbalFluency_C_instructions.mp4",
        "F": "VerbalFluency/VerbalFluency_F_CFL_instructions.mp4",
        "L": "VerbalFluency/VerbalFluency_L_instructions.mp4"
        },
    "F.A.S": {
        "F": "VerbalFluency/VerbalFluency_F_instructions.mp4",
        "A": "VerbalFluency/VerbalFluency_A_instructions.mp4",
        "S": "VerbalFluency/VerbalFluency_S_instructions.mp4"
        },
    "Semantic": {
        "Animals": "VerbalFluency/VerbalFluency_animals_instructions.mp4",
        "Food and Drinks": "VerbalFluency/VerbalFluency_Foodanddrink_instructions.mp4",
        "Fruits": "VerbalFluency/VerbalFluency_Fruits_instructions.mp4",
        "Tools": "VerbalFluency/VerbalFluency_tools_instructions.mp4"
        }
    }

