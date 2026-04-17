# -*- coding: utf-8 -*-
import serial

from rcp_task_acquisition.utils.constants import BAUDRATE, WRITE_TIMEOUT
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/Serial") 



class SerialDevice():
    def __init__(self):        
        self.serSuccess = False
        self.ser = None
        
        
    def init_serial(self):
        for i in range(2, 10):
            try:
                # self.ser = serial.Serial('/dev/ttyACM'+str(i), 
                #                          baudrate=self.baudrate, 
                #                          write_timeout = self.write_timeout)
                
                self.ser = serial.Serial('COM'+str(i),
                                         baudrate=BAUDRATE, 
                                         write_timeout = WRITE_TIMEOUT)
                self.serSuccess = True
                logger.info('Serial connected')
                break
            except:
                pass
            if self.serSuccess:
                break
        if not self.serSuccess:
            logger.info('Serial connection failed')
        
        
    def write(self, serial_str):
        self.ser.write(serial_str.encode())
        
    def close(self):
        if self.serSuccess:
            self.ser.close()
            self.serSuccess = False