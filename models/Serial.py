# -*- coding: utf-8 -*-
import serial
from utils.logger import get_logger
logger = get_logger("./models/Serial") 

class Serial():
    def __init__(self):
        
        self.serSuccess = False
        self.ser = None
        self.write_timeout = 0.1
        self.baudrate = 9600

    def init_serial(self):
        self.serSuccess = False
        for i in range(10):
            try:
                self.ser = serial.Serial('/dev/ttyACM'+str(i), 
                                         baudrate=self.baudrate, 
                                         write_timeout = self.write_timeout)
                self.serSuccess = True
                logger.info('Serial connected')
                break
            except:
                pass
            if self.serSuccess:
                break
        if not self.serSuccess:
            logger.info('Serial connection failed')
            