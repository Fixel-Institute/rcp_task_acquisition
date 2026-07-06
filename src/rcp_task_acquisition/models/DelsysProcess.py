from collections import deque
import threading
import time
import struct
import numpy as np

from library.Delsys.AeroPy import DataManager, TrignoBase

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/DelsysProcess")

class DataWriter():
    def __init__(self, filename):
        self.filename = filename
        self.fid = open(self.filename, 'wb+')
        self.thread_locker = threading.Lock()
        self.is_opened = True

    def write_data(self, key, value):
        data_type_bytes = key.encode('utf-8')
        time_bytes = struct.pack("<d", time.time())
        data_length_bytes = struct.pack("<II", len(data_type_bytes), len(value))
        with self.thread_locker:
            if self.is_opened:
                self.fid.write(b"RCPUF")
                self.fid.write(time_bytes)
                self.fid.write(data_length_bytes)
                self.fid.write(data_type_bytes)
                self.fid.write(value)

    def close(self):
        with self.thread_locker:
            self.fid.close()
            self.is_opened = False

class DelsysController():
    def __init__(self):
        super().__init__()
        self.EMGQueue = deque()
        self.IMUQueue = deque()
        self.AnalogQueue = deque()
        self.deque_locker = threading.Lock()
        self.Trigno = TrignoBase.TrignoBase(self)
        self.DataHandler = DataManager.DataKernel(self.Trigno)
        self.Trigno.DataHandler = self.DataHandler
        self.PauseFlag = True
        self.ResetBeforeConfig = True

        self.IsConnected = False
        self.IsScanning = False
        self.IsRecording = False

        self.StreamingThread = None
        self.WaitForStartThread = None
        self.WaitForStopThread = None

        self.DataWriter = None
        
        self.SensorList = []
        self.ActiveSensors = {}

        self.StreamingSensor = None
        self.IMUPreview = "ACC"

        # Callback
        self.update_sensors_config_ui = None

    def is_connected(self):
        return self.IsConnected

    def connect(self):
        if not self.IsConnected:
            try:
                self.Trigno.Connect_Callback()
                self.IsConnected = True
            except Exception as e:
                logger.error(f"Error connecting to Delsys device")
                raise e

        if self.update_sensors_config_ui is not None:
            self.update_sensors_config_ui({
                "IsConnected": self.IsConnected
            })

    def refresh(self):
        if not self.IsScanning:
            self.IsScanning = True
            device_types = self.Trigno.TrigBase.GetLinkDeviceNames(False)
            self.Trigno.TrigBase.SetAnalogInputConfig(1, True)
            self.Trigno.TrigBase.SetAnalogInputChannel(1, "Mic", 0)
            self.Trigno.TrigBase.ApplyAnalogInputSettings()

            try:
                self.Trigno.TrigBase.ScanSensors(False, device_types).Result
            except:
                logger.error("Error refreshing Delsys device")
            self.IsScanning = False

            sensor_status = {"Sensors": []}
            sensors = self.Trigno.TrigBase.GetSensors()
            for i in range(len(sensors)):
                sensor = sensors[i]
                try:
                    if sensor.InternalName == "Analog Input Adapter":
                        sensor.SelectSampleMode(sensor.Configuration.SampleModes[23])
                    elif sensor.InternalName == "FSR Adapter":
                        sensor.SelectSampleMode(sensor.Configuration.SampleModes[34])
                    else:
                        sensor.SelectSampleMode(sensor.Configuration.SampleModes[60])
                except Exception as e:
                    logger.error(f"Error configuring sample mode for sensor {sensor.InternalName}: {e}")

                try:
                    sensor_status["Sensors"].append({
                        "Id": sensor.PairNumber,
                        "Name": sensor.InternalName,
                        "TrignoChannels": [chan.Name for chan in sensor.TrignoChannels],
                    })
                except Exception as e:
                    logger.error(f"Error retrieving sensor information for sensor {sensor.InternalName}: {e}")
                    
            self.SensorList = sensor_status["Sensors"]
            print(self.SensorList)
            if self.update_sensors_config_ui is not None:
                self.update_sensors_config_ui(sensor_status)

            self.Trigno.TrigBase.SelectAllSensors() #Enable all sensors for streaming

    def configure_triggers(self):
        for i in range(4):
            self.Trigno.TrigBase.SetTrigger(False, i+1, True, False,  i)
        self.Trigno.TrigBase.SetSyncOutput(False, 1, True, 148)

    def start(self, filename="delsys_data.bin"):
        if self.IsRecording:
            logger.warning("Delsys device is already recording. Cannot start streaming.")
            return

        if self.DataWriter is not None and self.DataWriter.is_opened:
            self.DataWriter.close()

        self.DataWriter = DataWriter(filename)

        self.ActiveSensors = {}
        sensors = self.Trigno.TrigBase.GetSensors()
        for sensor in sensors:
            print(sensor.InternalName, sensor.IsSelected)
            if sensor.IsSelected:
                for channel in sensor.TrignoChannels:
                    guid = channel.Id.ToString()
                    self.ActiveSensors[guid] = {
                        "Name": channel.Name,
                        "SensorId": sensor.PairNumber,
                        "SamplingRate": channel.SampleRate,
                    }
                    self.DataWriter.write_data("Delsys_ChannelIDs", guid.encode('utf-8'))
                    self.DataWriter.write_data(guid + "|SensorId", struct.pack("<I", sensor.PairNumber))
                    self.DataWriter.write_data(guid + "|Name", channel.Name.encode('utf-8'))
                    self.DataWriter.write_data(guid + "|SamplingRate", struct.pack("<d", channel.SampleRate))
                    print(f"Active Sensor: {channel.Name}, SensorId: {sensor.PairNumber}, SamplingRate: {channel.SampleRate}")

        self.PauseFlag = False
        if self.ResetBeforeConfig and self.Trigno.TrigBase.GetPipelineState() == 'Armed':
            self.Trigno.TrigBase.ResetPipeline()
            self.ResetBeforeConfig = False

        if self.Trigno.TrigBase.GetPipelineState() == 'Armed':
            logger.info("Delsys device is already armed. Starting streaming.")
        elif self.Trigno.TrigBase.GetPipelineState() == 'Connected':
            self.configure_triggers()
            self.Trigno.TrigBase.Configure()

        configured = self.Trigno.TrigBase.IsPipelineConfigured()
        if not configured:
            logger.error("Delsys device is not configured. Cannot start streaming.")
            return

        self.Trigno.TrigBase.Start(False)
        self.IsRecording = True
        self.threadManager(False, False)

    def stop(self):
        if not self.IsRecording:
            logger.warning("Delsys device is not recording. Cannot stop streaming.")
            return

        self.PauseFlag = True
        self.Trigno.TrigBase.Stop()
        self.IsRecording = False
        self.DataWriter.close()
        logger.info("Delsys device stopped streaming.")
    
    def pair_sensor(self, sensor_id):
        self.Trigno.TrigBase.PairSensor(sensor_id)

    def get_sensors(self):
        sensor_ids = []
        for sensor in self.SensorList:
            if not sensor["Id"] in sensor_ids:
                sensor_ids.append(sensor["Id"])
        return sensor_ids

    def get_sensor_type(self, sensor_id):
        for key in self.ActiveSensors.keys():
            if self.ActiveSensors[key]["SensorId"] == sensor_id:
                if "Analog" in self.ActiveSensors[key]["Name"]:
                    print(f"Sensor {sensor_id} is of type {self.ActiveSensors[key]['Name']}")
                    return "Analog"
                
        return "Trigno"
    
    def set_streaming_analog(self, sensor_id):
        analog_fs = 1111.111
        analog_count = 0
        for key in self.ActiveSensors.keys():
            if self.ActiveSensors[key]["SensorId"] == sensor_id and "Analog" in self.ActiveSensors[key]["Name"]:
                analog_fs = self.ActiveSensors[key]["SamplingRate"]
                analog_count += 1

        self.StreamingSensor = sensor_id
        return analog_fs, analog_count

    def set_streaming_sensor(self, sensor_id, imu_type):
        emg_fs = 1250
        imu_fs = 148.148
        for key in self.ActiveSensors.keys():
            if self.ActiveSensors[key]["Name"] == f"EMG {sensor_id}":
                emg_fs = self.ActiveSensors[key]["SamplingRate"]
            elif self.ActiveSensors[key]["Name"] == f"Gyro {sensor_id}":
                imu_fs = self.ActiveSensors[key]["SamplingRate"]
        self.StreamingSensor = sensor_id

        if imu_type == "Accelerometer":
            self.IMUPreview = "ACC"
        else:
            self.IMUPreview = "GYRO"

        self.EMGQueue.clear()
        return emg_fs, imu_fs

    def get_streaming_data(self):
        if len(self.AnalogQueue) > 0:
            with self.deque_locker:
                print("test")
                analog_data = np.concatenate(self.AnalogQueue, axis=0)
                self.AnalogQueue.clear()
                if analog_data.shape[0] >= 10:
                    analog_data = np.mean(analog_data[-10:], axis=0)  # Take the mean of the last 10 samples
                else:
                    analog_data = np.mean(analog_data, axis=0)  # Take the mean of all available samples
                    
                return analog_data, np.zeros((0,3))
            
        if len(self.EMGQueue) > 0 and len(self.IMUQueue) > 0:
            with self.deque_locker:
                emg_data = np.concatenate(self.EMGQueue, axis=0)
                self.EMGQueue.clear()
                imu_data = np.concatenate(self.IMUQueue, axis=0)
                self.IMUQueue.clear()
                return emg_data, imu_data
        
        return np.zeros(0), np.zeros((0,3))

    def streaming(self):
        while self.PauseFlag:
            continue

        while not self.PauseFlag:
            if self.Trigno.TrigBase.CheckDataQueue():  # Is the DelsysAPI real-time data queue ready to retrieve
                try:
                    data_out = self.Trigno.TrigBase.PollDataByString()
                    if len(list(data_out.Keys)) > 0:
                        imu_stack = np.zeros((0,3))
                        analog_stack = np.zeros((0,4))
                        for key in list(data_out.Keys):
                            data = np.asarray(data_out[key], dtype='double')
                            self.DataWriter.write_data("Delsys_DataPacket|" + key, data.tobytes())
                            
                            if self.StreamingSensor is not None:
                                if key in self.ActiveSensors.keys():
                                    if self.ActiveSensors[key]["SensorId"] == self.StreamingSensor:
                                        if self.ActiveSensors[key]["Name"].startswith("EMG"):
                                            with self.deque_locker:
                                                self.EMGQueue.append(data)
                                        elif self.ActiveSensors[key]["Name"].startswith(f"{self.IMUPreview}"):
                                            if imu_stack.shape[0] == 0:
                                                imu_stack = np.zeros((len(data), 3))
                                            if self.ActiveSensors[key]["Name"].endswith("X"):
                                                imu_stack[:,0] = data
                                            elif self.ActiveSensors[key]["Name"].endswith("Y"):
                                                imu_stack[:,1] = data
                                            elif self.ActiveSensors[key]["Name"].endswith("Z"):
                                                imu_stack[:,2] = data
                                        elif self.ActiveSensors[key]["Name"].startswith("Analog"):
                                            if analog_stack.shape[0] == 0:
                                                analog_stack = np.zeros((len(data), 4))
                                            if self.ActiveSensors[key]["Name"].endswith(" 1"):
                                                analog_stack[:,0] = data
                                            elif self.ActiveSensors[key]["Name"].endswith(" 2"):
                                                analog_stack[:,1] = data
                                            elif self.ActiveSensors[key]["Name"].endswith(" 3"):
                                                analog_stack[:,2] = data
                                            elif self.ActiveSensors[key]["Name"].endswith(" 4"):
                                                analog_stack[:,3] = data
                                        
                        if imu_stack.shape[0] > 0:
                            with self.deque_locker:
                                self.IMUQueue.append(imu_stack)
                        
                        if analog_stack.shape[0] > 0:
                            with self.deque_locker:
                                self.AnalogQueue.append(analog_stack)

                            #print(self.ActiveSensors[key])
                            #if self.StreamingSensor is not None and self.ActiveSensors[key]["Name"] == "EMG" and self.ActiveSensors[key]["SensorId"] == self.StreamingSensor:
                            #    with self.deque_locker:
                            #        self.EMGQueue.append((self.ActiveSensors[key], data))
                                        
                except Exception as e:
                    print("Exception occured in GetData() - " + str(e))
            time.sleep(0.005)

    def waiting_for_start_trigger(self):
        while self.Trigno.TrigBase.IsWaitingForStartTrigger():
            continue
        self.PauseFlag = False
        logger.info("Trigger Start - Collection Started")

    def waiting_for_stop_trigger(self):
        while self.Trigno.TrigBase.IsWaitingForStartTrigger():
            continue
        while self.Trigno.TrigBase.IsWaitingForStopTrigger():
            continue

        self.PauseFlag = True
        logger.info("Trigger Stop - Collection Stopped")

    def threadManager(self, start_trigger, stop_trigger):
        """Handles the threads for the DataCollector gui"""
        self.EMGQueue = deque()

        self.StreamingThread = threading.Thread(target=self.streaming, daemon=True)
        self.StreamingThread.start()

        if start_trigger:
            self.WaitForStartThread = threading.Thread(target=self.waiting_for_start_trigger, daemon=True)
            self.WaitForStartThread.start()

        if stop_trigger:
            self.WaitForStopThread = threading.Thread(target=self.waiting_for_stop_trigger, daemon=True)
            self.WaitForStopThread.start()