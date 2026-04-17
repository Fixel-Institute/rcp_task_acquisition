# -*- coding: utf-8 -*-
from enum import Enum

class Answer(Enum):
    """Possible participant answers in the task."""
    SAME = "same"
    DIFFERENT = "different"
    NOGO = "nogo"

class Status(Enum):
    """Possible participant response in the task."""
    CORRECT = "correct"
    RESPONSE_ERROR = "response error"
    NO_RESPONSE = "no response"
    NO_GO_ERROR = "no_go error"