from psychopy import core

from rcp_task_acquisition.tasks import bases



class HardwareTest(bases.StimulusBase):
    def __init__(self, window, is_finished, frame, video_status):
        super().__init__(window, frame, video_status)
        self.finish = is_finished
        self.flash_time = 5
        
        
    def present(self):
        self.display.switch_patch()
        self.display.draw_patch()
        self.display.flip()
        clock = core.Clock()   
        while True:
            
            while clock.getTime() < self.flash_time:
                self.display.draw_patch()
                self.display.flip()
                if self.finish.value == 2:
                    self.display.switch_patch()
                    self.display.draw_patch()
                    self.display.flip()
                    self.finish.value = 0
                    return
            clock.reset(0)
            self.display.switch_patch()
            self.display.draw_patch()
            while clock.getTime() < self.flash_time:
                self.display.flip()
                if self.finish.value == 2:
                    self.finish.value = 0
                    return
            self.display.switch_patch()
            clock.reset()

        
    def saveMetadata(self, name, sessionFolder):
        pass
            