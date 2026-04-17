from rcp_task_acquisition.tasks import bases
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./tasks/ReachGrasp") 



class ReachGrasp(bases.StimulusBase):
    def __init__(self, window, frame, finish):
        super().__init__(window, frame)
        self.trial_count = 0
        self.hand = None
        self.grasp_object = None
        self.finish = finish
        self.hand_dict = {}
        self.grasp_dict = {}
        
    def present(self):        
        self.trial_count+=1
        self.trial
        self.hand_dict[f"trial_{self.trial_count}"] = self.hand
        self.grasp_dict[f"trial_{self.trial_count}"] = self.grasp_object
        # PARAMS["hand_used"][f"trial_{self.trial_count}"] = self.hand
        # PARAMS["grasp_object"][f"trial_{self.trial_count}"] = self.grasp_object
        self.play_tone()
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()

        while self.finish.value == 0:
            self.display.draw_patch()
            self.display.flip()        

        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()        
        self.play_tone()

        
        
    def update_data(self, data):
        self.hand = data[0]    
        self.grasp_object = data[1]   
                 
        
    def saveMetadata(self, name, sessionFolder):
        data = {"trial_count": self.trial_count, 
                "hand_used": self.hand_dict,
                "grasp_object": self.grasp_dict
            }        
        return data
            
            