# -*- coding: utf-8 -*-

# SARA constants
# in assesments lists, first list is the scoring criteria, while the second is whether or not to include hand choice
ASSESMENTS = {
    "gait": {
             0: "Normal, no difficulties in walking, turning, and walking tandem (up to one misstep allowed)",
             1: "Slight difficulties, only visible when walking 10 consecutive steps in tandem",
             2: "Clearly abnormal, tandem walking >10 steps not possible",
             3: "Considerable staggering, difficulties in half-turn, but without support",
             4: "Marked staggering, intermittent support of the wall required",
             5: "Severe staggering, permanent support of one stick or light support by one arm required",
             6: "Walking >10 m only with strong support (two special sticks or stroller or accompanying person)",
             7: "Walking <10 m only with strong support (two special sticks or stroller or accompanying person)",
             8: "Unable to walk, even supported"
             },
    "stance": {
             0: "Normal, able to stand in tandem for >10 s",
             1: "Able to stand with feet together without sway, but not in tandem for >10 s",
             2: "Able to stand with feet together for >10 s, but only with sway",
             3: "Able to stand for >10 s without support in natural position, but not with feet together",
             4: "Able to stand for >10 s in natural position only with intermittent support",
             5: "Able to stand >10 s in natural position only with constant support of one arm",
             6: "Unable to stand for >10 s even with constant support of one arm"
             },
    "sitting": {
             0: "Normal, no difficulties sitting >10 s",
             1: "Slight difficulties, intermittent sway",
             2: "Constant sway, but able to sit >10 s without support",
             3: "Able to sit for >10 s only with intermittent support",
             4: "Unable to sit for >10 s without continuous support"
             },
    "speech disturbance": {
             0: "Normal",
             1: "Suggestion of speech disturbance",
             2: "Impaired speech, but easy to understand",
             3: "Occasional words difficult to understand",
             4: "Many words difficult to understand",
             5: "Only single words understandable",
             6: "Speech unintelligible / anarthria"
             },
    "finger chase left": {
             0: "No dysmetria",
             1: "Dysmetria, under/overshooting target <5 cm",
             2: "Dysmetria, under/overshooting target <15 cm",
             3: "Dysmetria, under/overshooting target >15 cm",
             4: "Unable to perform 5 pointing movements"
             },
    "finger chase right": {
             0: "No dysmetria",
             1: "Dysmetria, under/overshooting target <5 cm",
             2: "Dysmetria, under/overshooting target <15 cm",
             3: "Dysmetria, under/overshooting target >15 cm",
             4: "Unable to perform 5 pointing movements"
             },
    "nose-finger test left": {
             0: "No tremor",
             1: "Tremor with an amplitude <2 cm",
             2: "Tremor with an amplitude <5 cm",
             3: "Tremor with an amplitude >5 cm",
             4: "Unable to perform 5 pointing movements"
             },
    "nose-finger test right": {
             0: "No tremor",
             1: "Tremor with an amplitude <2 cm",
             2: "Tremor with an amplitude <5 cm",
             3: "Tremor with an amplitude >5 cm",
             4: "Unable to perform 5 pointing movements"
             },
    "fast alternating hand movements left": {
             0: "Normal, no irregularities (performs <10 s)",
             1: "Slightly irregular (performs <10 s)",
             2: "Clearly irregular, single movements difficult to distinguish or relevant interruptions, but performs <10 s",
             3: "Very irregular, single movements difficult to distinguish or relevant interruptions, performs >10 s",
             4: "Unable to complete 10 cycles"
            },
    "fast alternating hand movements right": {
             0: "Normal, no irregularities (performs <10 s)",
             1: "Slightly irregular (performs <10 s)",
             2: "Clearly irregular, single movements difficult to distinguish or relevant interruptions, but performs <10 s",
             3: "Very irregular, single movements difficult to distinguish or relevant interruptions, performs >10 s",
             4: "Unable to complete 10 cycles"
            },
    "heel-shin slide left": {
             0:"Normal",
             1: "Slightly abnormal, contact to shin maintained",
             2: "Clearly abnormal, goes off shin up to 3 times during 3 cycles",
             3: "Severely abnormal, goes off shin 4 or more times during 3 cycles",
             4: "Unable to perform the task"
             },
    "heel-shin slide right": {
             0:"Normal",
             1: "Slightly abnormal, contact to shin maintained",
             2: "Clearly abnormal, goes off shin up to 3 times during 3 cycles",
             3: "Severely abnormal, goes off shin 4 or more times during 3 cycles",
             4: "Unable to perform the task"
             },
    }
