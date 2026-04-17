'''
A class to store the labjack events and functions that are controlled from the 
frontend. 
'''
import wx
import time
import numpy as np
import ctypes
from multiprocessing import Queue, Array, Value

from rcp_task_acquisition.utils.constants import PLOT_CONSTANTS
from rcp_task_acquisition.models.LabjackProcess import LabJackDataStream
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/LabjackFrontend") 

 

class LabjackFrontend():
    def __init__(self, array_length, ctrl_panel, timer, args, button_pressed, press_count, hardware_test):
        
        self.constants = []
        self.button_pressed = button_pressed #Value(ctypes.c_bool, False)
        self.labjack_list = [item for item in list(args[1]) if item not in self.constants] #list(args[1])
        self.hardware = [item for item in list(args[0]) if item not in PLOT_CONSTANTS] #list(args[0])
        self.hardware_indices=[Value(ctypes.c_int, -1), Value(ctypes.c_int, -1), Value(ctypes.c_int, -1)]
        self.prev_graph_list = [-1, -1, -1]
        self.digital_list = []
        self.analog_list = []
        self.button_list = []
        self.extended_list = []
        self.array_length = array_length
        for index, item in enumerate(self.labjack_list):
            if "F" in item:
                self.digital_list.append(int(item[-1]))
                logger.debug(f"hardware: {self.hardware[index]}")
                if "Button" in self.hardware[index]:
                    self.button_list.append(int(item[-1])) 
            else:
                self.analog_list.append(item)
        self.inputs_list = [self.analog_list, self.digital_list]     
        self.labjack_arr = Array('d', array_length*(len(self.hardware_indices)+3))
        self.labjack_queue = Queue()
        self.labjack_is_csv  = Value(ctypes.c_bool, False)
        self.stream_started = Value(ctypes.c_bool, False)
        self.labjack_is_finished = Value(ctypes.c_bool, True)
        self.scan_rate = Value(ctypes.c_float, 0)
        self.hardware_test = hardware_test
        self.graph_panel = ctrl_panel
        self.labjack_choices = self.graph_panel.get_graph_choices()
        self.labjack_timer = timer
        self.press_count = press_count
        logger.debug(f"button {self.button_list}")
        self.graph_panel.set_constants(self.constants)
        for choice in self.labjack_choices:
            choice.Bind(wx.EVT_CHOICE, self._update_graph_list)
        self.handshake = Value(ctypes.c_int, False)
        self.serial_state = 0
        self.serial_bool = False
        self.ser_success = False


    def labjack_stream(self, event):
        labjack_button = self.graph_panel.get_graph_button()
        if labjack_button.GetValue():
            labjack_button.SetLabel("Stop Labjack")
            self.stop_labjack()
            self.start_labjack()
        else:
            self.stop_labjack()
            labjack_button.SetLabel("Stream Labjack")
            labjack_button.SetValue(False)
       
    def update_hardware(self,hardware_lists):
        self.all_hardware = hardware_lists
        self.graph_panel.update_graph(hardware_lists)
        self.constant_index = []
        self.constants = []
        if list(hardware_lists[1]):
            for index, constant in enumerate(PLOT_CONSTANTS):
                hardware_index = list(hardware_lists[0]).index(constant)
                self.constants.append(hardware_lists[1][hardware_index])
                self.constant_index.append(hardware_index)
               
        self.labjack_list = [item for item in list(hardware_lists[1]) if item not in self.constants] #list(args[1])
        self.hardware = [item for item in list(hardware_lists[0]) if item not in PLOT_CONSTANTS] #list(args[0])
        self.labjack_list = self.all_hardware[1]
        self.hardware = self.all_hardware[0]
        self.digital_list = []
        self.analog_list = []
        self.button_list = []
        self.extended_list = []
        for index, item in enumerate(list(self.all_hardware[1])):
            if "F" in item:
                self.digital_list.append(int(item[-1]))
                logger.debug(f"hardware: {self.all_hardware[1][index]}")
                if "Button" in self.all_hardware[0][index]:
                    self.button_list.append((int(item[-1]), "f")) 
            elif "E" in item:
                self.extended_list.append(int(item[-1]))
                if "Button" in self.all_hardware[0][index]:
                    self.button_list.append((int(item[-1]), "e")) 
            else:
                self.analog_list.append(item)
        self.inputs_list = [self.analog_list, self.digital_list, self.extended_list]     
        logger.debug(self.button_list)
        self._update_graph_list('')
        
        
    def start_labjack(self):
        if not self.labjack_is_finished.value:
            logger.info("labjack is currently runninng")
            return True
        self.scan_rate.value = 0
        self.labjack_is_finished.value = False
        self.labjack_process = LabJackDataStream(self.array_length, 
                                                 self.labjack_is_finished,
                                                 self.labjack_arr, 
                                                 self.labjack_is_csv, 
                                                 self.labjack_queue,
                                                 self.labjack_list,
                                                 self.hardware_indices,
                                                 self.button_pressed,
                                                 self.inputs_list,
                                                 self.button_list,
                                                 self.press_count,
                                                 self.constant_index,
                                                 self.all_hardware[3],
                                                 self.stream_started,
                                                 self.scan_rate,
                                                 self.handshake)

        if self.labjack_process.is_successful():
            self.labjack_process.start()
            self.labjack_timer.Start(200)
            return True
        else:
            # Warning("labjack").display()
            labjack_button = self.graph_panel.get_graph_button()
            labjack_button.SetValue(False)
            return False
        



    def stop_labjack(self):
        
        
        self.labjack_is_finished.value = True
        self.labjack_is_csv.value = False
        self.stream_started.value = False
        self.labjack_timer.Stop()
        for index, lj_input in enumerate(self.hardware_indices):
            self.graph_panel.update_yaxis([np.nan]*self.array_length, index, lj_input.value)
        for index, constant_inputs in enumerate(self.constants):
            
            self.graph_panel.update_constants([np.nan]*self.array_length, index, self.constant_index[index])
        new_arr = np.empty(80000*(len(self.hardware_indices)+3))

        new_arr.fill(np.nan)
        
        np.frombuffer(self.labjack_arr.get_obj(), dtype=ctypes.c_double).reshape(len(new_arr.flatten()))[:] = new_arr.flatten()
        self.graph_panel.draw()
        try:
            self.labjack_process.join()
        except:
            logger.info("No open Labjack process")
        logger.info('labjack_stopped')
        return self.scan_rate.value

    def labjack_event(self, event):
            if not self.labjack_is_finished.value and self.stream_started.value:
                arr_step = 0
                # if self.handshake.value == 1:
                y_plot_points = np.frombuffer(self.labjack_arr.get_obj(), 'd', len(self.labjack_arr))
                # else:
                #     return
                if not np.isnan(y_plot_points[-1]) and self.serial_bool:
                    self.serial_state += 1
                    if self.ser_success and self.serial_state > 0:
                        self.ser.write(self.msg.encode())
                        
                        time.sleep(2)
                        self.ser_success = False
                        self.serial_bool = False
                        self.ser.write("A".encode())
                
                    
                if not self.hardware_test.value:
                    for index, lj_input in enumerate(self.hardware_indices):
                        if lj_input.value == -1:
                            self.graph_panel.update_yaxis([np.nan]*self.array_length, index, lj_input.value)
                            y_plot_points[arr_step:arr_step+self.array_length] = np.nan
                            # arr_step+= self.array_length
                            self.graph_panel.set_visible(index, False)
                        else:
                            if lj_input.value != self.prev_graph_list[index]:
                                self.prev_graph_list[index] = lj_input.value
                                y_plot_points[arr_step:arr_step+self.array_length] = np.nan
                                self.graph_panel.update_yaxis([np.nan]*self.array_length, index, lj_input.value)
                            self.graph_panel.update_yaxis(y_plot_points[arr_step:arr_step+self.array_length], index, lj_input.value)
                            self.graph_panel.set_visible(index)
                        arr_step+= self.array_length
                else:
                    
                    for index, lj_input in enumerate(self.hardware_indices):
                        self.graph_panel.set_visible(index, False)
                        arr_step += self.array_length
                     
                for index, constants_input in enumerate(self.constants):
                    self.graph_panel.update_constants(y_plot_points[arr_step:arr_step+self.array_length], index, self.constant_index[index])
                    self.graph_panel.set_visible_const(index)
                    arr_step+= self.array_length
                # if self.handshake.value == 1:    
                np.frombuffer(self.labjack_arr.get_obj(), dtype=ctypes.c_double).reshape(len(y_plot_points.flatten()))[:] = y_plot_points.flatten()
                    # self.handshake.value = 0
                self.graph_panel.draw()
                
        
    def add_csv(self, labjack_file, serial, msg):
        self.labjack_csv = labjack_file
        self.labjack_queue.put(labjack_file)
        self.labjack_is_csv.value = True
        
        self.serial_state = 0
        self.serial_bool = True
        self.ser_success = serial.serSuccess
        self.ser = serial.ser
        self.msg = msg
        
        
    def is_active(self):
        return not self.labjack_is_finished.value
    
    def _update_graph_list(self, event):
        selected_list = []

        for choice in self.labjack_choices:
            if choice.GetSelection() !=-1 and choice.GetSelection() !=0:
                selection = choice.GetSelection()
                choices =  choice.GetStrings()
                selection = choices[selection]
                original_selection = self.hardware.index(selection)
                selected_list.append(original_selection)
        for index, choice in enumerate(self.labjack_choices):
            try:
                selection = choice.GetSelection() if choice.GetSelection() != 0 else -1
                if selection != -1:
                    choices =  choice.GetStrings()
                    selection = choices[selection]
                    original_selection = self.hardware.index(selection)
                else:
                    original_selection = -1
                new_options = [hardware for index, hardware in enumerate(self.hardware) if index not in selected_list or index == original_selection]
                new_options.insert(0, " ")
                choice.SetItems(new_options)
                
                if selection !=-1:
                    choice.SetSelection(new_options.index(selection))
                self.hardware_indices[index].value = original_selection
                self.graph_panel.update_label(index, selection)
            except Exception as e:
                logger.error(e)
    