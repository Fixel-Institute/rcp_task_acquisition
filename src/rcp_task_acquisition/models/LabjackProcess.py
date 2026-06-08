from multiprocessing import Process
import numpy as np
import ctypes
import win32api,win32process,win32con

from labjack import ljm
from rcp_task_acquisition.utils.constants import SCANS_PER_READ
from rcp_task_acquisition.utils.logger import get_logger

logger = get_logger("./models/LabjackProcess") 

class LabJackDataStream(Process):
    def __init__(self, arr_length, is_finished, labjack_arr, 
                 create_csv, folder_queue, labjack_list, graph_indices, 
                 button_pressed, inputs, button_list, press_counter,
                 constants, voltage_ranges, stream_started, scan_rate, handshake):
        self.voltage_range = {}
        for index, val in enumerate(labjack_list):
            if "A" in val:
                self.voltage_range[val] = voltage_ranges[index]
        logger.debug(self.voltage_range)
        super().__init__()
        self.arr_length = arr_length
        self.attemptedscanRate = 40000
        self.button_pressed = button_pressed
        self.press_counter = press_counter
        self.analog_inputs  = inputs[0]
        self.digital_inputs = inputs[1]
        self.extended_inputs = inputs[2]
        self.stream_started = stream_started
        self.actualscanRate = scan_rate
        self.handshake = handshake
        for item in self.extended_inputs:
            self.digital_inputs.append(item+8)
        logger.debug(f"analog: {self.analog_inputs}, digital: {self.digital_inputs}, extended: {self.extended_inputs}")

        self.scan_list = self.analog_inputs
        self.scan_num = len(self.scan_list) 
        if self.digital_inputs:
            self.scan_num+=1
        logger.debug(self.extended_inputs)
        logger.debug(self.digital_inputs)
        self.graph_arr = labjack_arr
        self.numpy_arr = np.empty((6, self.attemptedscanRate*2))
        self.numpy_arr.fill(np.nan)
        self.finished = is_finished
        self.create_csv = create_csv
        self.folder_queue = folder_queue
        self.session_file = ''
        self.labjack_csv= None
        self.results = np.empty(self.scan_num*SCANS_PER_READ)
        self.results.fill(np.nan)
        self.graph_indices = graph_indices
        self.prev_graphs = [index.value for index in self.graph_indices]
        self.button_list = button_list
        self.constants = constants
        self.extended = False
        self.voltage_ranges = []
        aScanList = ljm.namesToAddresses(len(self.scan_list), self.scan_list)[0]
        if self.digital_inputs or self.extended_inputs:
            aScanList.append(2580)

        input_names = []
        voltage_ranges = []
        for key in self.voltage_range:
            input_names.append(f"{key}_RANGE")
            voltage_ranges.append(float(self.voltage_range[key][1]))
        input_names.append("STREAM_CLOCK_SOURCE")
        voltage_ranges.append(0)
        self.input_names = input_names
        self.voltage_ranges = voltage_ranges

    def test_connection():
        is_connected = False
        try:
            handle = ljm.openS("ANY", "ANY", "ANY")
            info = ljm.getHandleInfo(handle)
            print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
                "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
                (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
            
            # Stream Configuration
            aScanListNames = ["AIN0"]
            numAddresses = len(aScanListNames)
            aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
            scanRate = 1000
            scansPerRead = int(scanRate / 10)
            
            ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)
            ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)
            aNames = ["AIN0_RANGE", "STREAM_RESOLUTION_INDEX"]
            aValues = [10.0, 0]

            numFrames = len(aNames)
            ljm.eWriteNames(handle, numFrames, aNames, aValues)
            scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
            ret = ljm.eStreamRead(handle)
            ljm.close(handle)
            is_connected = True
        
        except Exception as e:
            print(e)
        
        if not is_connected:
            # USB\VID_0CD5&PID_0008\6&223C19BF&0&2
            return False
            
        return True

    def run(self):
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
        first_write = True
        logger.debug("Start labjack stream.")
        write_to_csv = False
        data_1= None
        data_2 = None
        debounce = 0
        min_off_samples = int(round(self.attemptedscanRate*0.01)) # minimum button release duration

        aScanList = ljm.namesToAddresses(len(self.scan_list), self.scan_list)[0]
        if self.digital_inputs or self.extended_inputs:
            aScanList.append(2580)
        logger.debug(aScanList)
        numAddresses  = len(aScanList)
        try:
            self.handle = ljm.openS("ANY", "ANY", "ANY")
            ljm.writeLibraryConfigS("LJM_STREAM_TCP_RECEIVE_BUFFER_SIZE", 4194304)
            ljm.eWriteNames(self.handle, len(self.input_names), self.input_names, self.voltage_ranges)
            self.actualscanRate.value = ljm.eStreamStart(self.handle, SCANS_PER_READ, numAddresses, aScanList, self.attemptedscanRate)
        except:
            ljm.closeAll()
            self.handle = ljm.openS("ANY", "ANY", "ANY")
            ljm.writeLibraryConfigS("LJM_STREAM_TCP_RECEIVE_BUFFER_SIZE", 4194304)
            ljm.eWriteNames(self.handle, len(self.input_names), self.input_names, self.voltage_ranges)
            self.actualscanRate.value = ljm.eStreamStart(self.handle, SCANS_PER_READ, numAddresses, aScanList, self.attemptedscanRate)
        
        logger.info(f"Labjack stream started at {self.actualscanRate.value} scans/s")

        self.stream_started.value = True
        while not self.finished.value:
            if self.create_csv.value:
                self.labjack_csv = self.folder_queue.get()
                write_to_csv = True
                self.create_csv.value = False
            data = ljm.eStreamRead(self.handle)
            self.results[:] = np.asarray(data[0])
            if int(-9999) in self.results:
                logger.warn("ERROR!! OVERFLOW!!")
                # return
                logger.warn(f"prev data[1]: {data_1}")
                logger.warn(f"prev data[2]: {data_2}")
                logger.warn(f"data[1]: {data[1]}")
                logger.warn(f"data[2]: {data[2]}")
            data_1 = data[1]
            data_2 = data[2]
            if int(data[1]) > 48:
                logger.debug(f"buffer value:  {data[1]}")
            results = self.results.reshape((self.scan_num, SCANS_PER_READ), order="F")

            ints = results[-1].astype(np.uint16)
            new_list = np.unpackbits(ints.view(np.uint8), bitorder="little").reshape(16, SCANS_PER_READ, order = "F")#[::-1]

            if self.button_list:
                for button in self.button_list:
                    reshape_list = new_list
                    
                    self.button_pressed.value = not np.all(reshape_list[button[0]])
                    if debounce == 0:
                        if self.button_pressed.value:
                            self.press_counter.value += 1
                            logger.debug(f"press#: {self.press_counter.value}")
                            debounce = 1
                    if np.all(reshape_list[button[0]][-min_off_samples:]):
                        debounce = 0
            if write_to_csv:
                self.write_csv( results, first_write)
                first_write = False
            self.graph(results, new_list) #digital_reshape, extended_reshape)           

        
        self.stop()


    def graph(self, results, digital): #, extended): 
        new_list = []
        new_list = [digital[item] for item in self.digital_inputs]
        

        new_results = np.vstack((results[:-1], new_list))
        for index, labjack_index in enumerate(self.graph_indices):
            
            if labjack_index.value == -1:
                self.numpy_arr[index].fill(np.nan)
                continue 
            else:
                if labjack_index.value != self.prev_graphs[index]:
                    self.numpy_arr[index].fill(np.nan)
                    
            
                size = len(new_results[labjack_index.value])
            self.prev_graphs[index] = labjack_index.value
        graph_list_index = 0

        for index, labjack_index in enumerate(self.graph_indices):
            size = len(new_results[labjack_index.value])
            self.numpy_arr[index] = np.roll(self.numpy_arr[index], size)
            self.numpy_arr[index][:size] = np.flip(np.asarray(new_results[labjack_index.value]))
            self.prev_graphs[index] = labjack_index.value
            graph_list_index += 1
        for index, constants_index in enumerate(self.constants):
            size = len(new_results[constants_index])
            self.numpy_arr[graph_list_index] = np.roll(self.numpy_arr[graph_list_index], size)
            self.numpy_arr[graph_list_index][:size] = np.flip(np.asarray(new_results[constants_index]))
            graph_list_index += 1

        np.frombuffer(self.graph_arr.get_obj(), dtype=ctypes.c_double).reshape(len(self.numpy_arr.flatten()))[:] = self.numpy_arr.flatten()



    def write_csv(self, results, write_headers=False): 
        if not self.labjack_csv:
            self.labjack_csv = self.session_file #os.path.join(self.sessionFolder, filename)
        with open(self.labjack_csv, 'ab') as file:
            if write_headers:
                headers = self.analog_inputs
                if self.digital_inputs:
                    headers.append("Digital")
                np.savetxt(file, np.asarray(headers).reshape(1, len(headers)), fmt="%s", delimiter=",")
            np.savetxt(file, results.T, fmt="%f", delimiter=",")
            
            
    def set_folder(self, session_dir):
        self.session_file = session_dir


    def stop(self):
        try:
            ljm.eStreamStop(self.handle)
        except:
            logger.debug("labjack stream already stopped")
        self.create_csv.value = False
        self.session_file = ""
        self.labjack_csv = ""
        self.numpy_arr[:] = np.nan
        ljm.closeAll()
    
    def is_successful(self):
        return True
        
