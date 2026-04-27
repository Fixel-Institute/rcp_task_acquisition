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
        self.DataQueue = deque()
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

        self.ActiveSensors = {}

        # Callback
        self.update_sensors_config_ui = None

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
            try:
                self.Trigno.TrigBase.ScanSensors(False, device_types).Result
            except:
                logger.error("Error refreshing Delsys device")
            self.IsScanning = False

            if self.update_sensors_config_ui is not None:
                sensor_status = {"Sensors": []}
                sensors = self.Trigno.TrigBase.GetSensors()
                for i in range(len(sensors)):
                    sensor = sensors[i]
                    if sensor.InternalName == "Analog Input Adapter":
                        sensor.SelectSampleMode(sensor.Configuration.SampleModes[23])
                    else:
                        sensor.SelectSampleMode(sensor.Configuration.SampleModes[60])

                    sensor_status["Sensors"].append({
                        "Id": sensor.PairNumber,
                        "Name": sensor.InternalName,
                        "TrignoChannels": [chan.Name for chan in sensor.TrignoChannels],
                    })

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

    def streaming(self):
        self.DataQueue = deque()

        while self.PauseFlag:
            continue

        while not self.PauseFlag:
            if self.Trigno.TrigBase.CheckDataQueue():  # Is the DelsysAPI real-time data queue ready to retrieve
                try:
                    data_out = self.Trigno.TrigBase.PollDataByString()
                    if len(list(data_out.Keys)) > 0:
                        for key in list(data_out.Keys):
                            self.DataWriter.write_data("Delsys_DataPacket|" + key, np.asarray(data_out[key], dtype='double').tobytes())

                except Exception as e:
                    print("Exception occured in GetData() - " + str(e))

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
        self.StreamingThread = threading.Thread(target=self.streaming)
        self.StreamingThread.start()

        if start_trigger:
            self.WaitForStartThread = threading.Thread(target=self.waiting_for_start_trigger)
            self.WaitForStartThread.start()

        if stop_trigger:
            self.WaitForStopThread = threading.Thread(target=self.waiting_for_stop_trigger)
            self.WaitForStopThread.start()