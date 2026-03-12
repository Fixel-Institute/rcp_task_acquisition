# -*- coding: utf-8 -*-
from threading import Thread
from queue import Empty
import cv2
from models.Warnings import Warning
from utils.logger import get_logger
logger = get_logger("./models/VideoThread") 







class VideoThread(Thread):
    def __init__(self, video_queue, file_path, width, height, fps):
        Thread.__init__(self, name=file_path, daemon=True)
        self.active = True
        self.video_queue = video_queue
        self.width = width
        self.height = height
        self.fps = round(fps,2)
        self.video_writer = None
        self.video_file = file_path
        self.num_frames = 0
        self.name = file_path.split("/")[-1]
        self.timestamps = None
    
    
    def run(self):
        
        self.prepare_writers()
        
        while self.active:
            try:
                queue_list = self.video_queue.get(timeout=0.05)
            except Empty:
                continue
            
            if len(queue_list) == 0:
                self.close_writers()
        
        
            for frame in queue_list:
                if self.video_writer == None:
                    self.prepare_writers()
                self.video_writer.write(frame)
                # print(f"{self.name}: {self.num_frames}")
                self.num_frames+=1
        try:
            print(self.video_queue.qsize())
            queue_list = self.video_queue.get(timeout=0.05)
            # print(queue_list)
            if type(queue_list) == int:
                self.close_writers()
                return
            for frame in queue_list:
                self.video_writer.write(frame)
                # print(f"{self.name}: {self.num_frames}")
                self.num_frames+=1
        except Empty:
            pass
        
        self.close_writers()
        print('here- end')
        
        
    def prepare_writers(self):
        video_file = self.video_file+".mp4"
        self.video_writer = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), self.fps, (self.width, self.height))
        
    
    def close_writers(self):
        if self.video_writer != None:
            self.video_writer.release()
        
        # cap = cv2.VideoCapture(self.video_file+".mp4")
        # length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # logger.info(f"{self.name}: mp4 frames: {self.num_frames}, timestamps file lenth: {self.timestamps}")
        # if self.num_frames != self.timestamps+1:
        #     warn_str = f"{self.name}: video length ({self.num_frames}) and timestamps files ({self.timestamps+1}) do not match."
        #     print("WARNING: ", warn_str)
            # warning = Warning("frames", warn_str)
            # warning.display()
        self.video_file = self.video_writer = None
        self.video_queue.put(self.num_frames)
    
    def cancel(self):
        self.active = False
        # self.timestamps = timestamps
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    