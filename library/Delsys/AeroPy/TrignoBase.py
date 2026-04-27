"""
This class creates an instance of the Trigno base. Put your key and license here.
"""
import threading
import time
from pythonnet import load
from enum import Enum
from dataclasses import dataclass

load("coreclr")
import clr

clr.AddReference("library\\Delsys\\resources\\DelsysAPI")
clr.AddReference("System.Collections")

from Aero import AeroPy

#key = ""
#license = ""

class TrignoType(Enum):
    LITE = 0
    CENTRO = 1
    BASESTATION = 2

@dataclass
class Sensor:
    name: str #sensor name
    pair_number : int #number when last paired to the trigno receiver
    mode : str #current mode
    channels : list #channel information for the sensor

@dataclass
class Channel:
    name: str
    is_enabled : bool
    channel_type : str
    sample_rate : float
    guid : str


class TrignoBase:
    """
    AeroPy reference imported above then instantiated in the constructor below
    All references to TrigBase. call an AeroPy method (See AeroPy documentation for details)
    """

    def __init__(self, collection_data_handler):
        self.TrigBase = AeroPy()
        self.collection_data_handler = collection_data_handler
        self.channel_guids = []
        self.channelcount = 0
        self.pairnumber = 0
        self.data_writer = None # TODO: add data writer class and initialize here
        self.trigno_station_type: TrignoType
        self.reset_before_config : bool = True
        self.sensors = []

    # -- AeroPy Methods --
    def PipelineState_Callback(self):
        return self.TrigBase.GetPipelineState()

    def Connect_Callback(self):
        """Callback to connect to the base"""
        self.TrigBase.ValidateBase(key, license)
        station_type = self.TrigBase.GetTrignoReceiverType()
        match station_type:
            case "Trigno Centro":
                self.trigno_station_type = TrignoType.CENTRO
            case "Trigno Lite":
                self.trigno_station_type = TrignoType.LITE
            case "Trigno Base Station":
                self.trigno_station_type = TrignoType.BASESTATION

    def Pair_Callback(self):
        return self.TrigBase.PairSensor(self.pairnumber)

    def CheckPairStatus(self):
        return self.TrigBase.CheckPairStatus()

    def CheckPairComponentAdded(self):
        return self.TrigBase.CheckPairComponentAdded()

    def scan_callback(self, link_controller):
        """Callback to tell the base to scan for any available sensors"""
        try:
            self.TrigBase.ScanSensors(link_controller.use_ant, link_controller.get_device_types()).Result
        except Exception:
            print("Python demo attempt another scan...")
            time.sleep(1)
            self.scan_callback(link_controller)
        self.TrigBase.SelectAllSensors() #Enable all sensors for streaming
        self.set_sensors_list()

    def set_sensors_list(self):
        self.sensors.clear()
        aero_sensors = self.TrigBase.GetSensors()
        for sensorIndex in range(len(aero_sensors)):
            name = aero_sensors[sensorIndex].FriendlyName
            pair_number = self.TrigBase.GetSensorPairNumber(sensorIndex)
            mode = self.TrigBase.GetCurrentSensorMode(sensorIndex)
            channels = []
            channel_info = self.TrigBase.GetSensorChannelInfo(sensorIndex)
            for c in channel_info:
                channel_name = c["Name"]
                channel_enabled = c["Enabled"] == 'True'
                channel_type = c["Type"]
                channel_sample_rate = float(c["Sample Rate"])
                channel_guid = c["Guid"]
                channels.append(Channel(channel_name, channel_enabled, channel_type, channel_sample_rate, channel_guid))
            self.sensors.append(Sensor(name=name, pair_number= pair_number, mode= mode, channels= channels))
        self.print_sensors_found()

    def print_sensors_found(self):
        for sensor in self.sensors:
            str_pair = f"({str(sensor.pair_number)}) " if sensor.pair_number > 0 else ""
            str_mode = f"mode: {str(sensor.mode)}" if sensor.mode != "" else ""
            print(f"{str_pair}{sensor.name} {str_mode}")
            for channel in sensor.channels:
                str_rate = f"({channel.sample_rate} Hz) " if float(channel.sample_rate) > 0 else ""
                print(f"--- {channel.name} {str_rate}{channel.guid}")

    def Start_Callback(self, start_trigger, stop_trigger, trigger_controller, analog_input_controller):
        match self.trigno_station_type:
            case TrignoType.CENTRO:
                self.start_centro(trigger_controller, analog_input_controller)
            case _:
                self.start_base(start_trigger, stop_trigger)

    def start_base(self, start_trigger : bool, stop_trigger : bool):
        """Callback to start the data stream from Sensors"""
        self.start_trigger = start_trigger
        self.stop_trigger = stop_trigger
        configured = self.ConfigureCollectionOutput()
        if configured:
            #(Optional) To get YT data output pass 'True' to Start method
            self.TrigBase.Start(self.collection_data_handler.streamYTData)
            self.collection_data_handler.threadManager(self.start_trigger, self.stop_trigger)

    def start_centro(self, trigger_controller, analog_input_controller):
        self.start_trigger = trigger_controller.start_input.is_enabled
        self.stop_trigger  = trigger_controller.stop_input.is_enabled
        self.configure_analog_input(analog_input_controller.get_num_channels(),
                                    analog_input_controller.is_mic_enabled(),
                                    analog_input_controller.get_voltage_ranges(),
                                    analog_input_controller.get_channel_names())
        for trigger_state in trigger_controller.get_centro_trigger_config():
            self.TrigBase.SetTrigger(trigger_state[0],  # is it enabled
                                     trigger_state[1],  # channel (1-indexed)
                                     trigger_state[2],  # is it 5V
                                     trigger_state[3],  # is it a rising edge signal
                                     trigger_state[4])  # trigger type
        sync_output = trigger_controller.get_sync_output()
        self.TrigBase.SetSyncOutput(sync_output[0],  # is it enabled
                                    sync_output[1],  # channel (1-indexed)
                                    sync_output[2],  # is it 5V
                                    sync_output[3])  # frequency
        configured = self.ConfigureCollectionOutput()
        if configured:
            # (Optional) To get YT data output pass 'True' to Start method
            self.TrigBase.Start(self.collection_data_handler.streamYTData)
            self.collection_data_handler.threadManager(self.start_trigger, self.stop_trigger)

    def ConfigureCollectionOutput(self):
        if not self.start_trigger:
            self.collection_data_handler.pauseFlag = False
        if self.reset_before_config and self.TrigBase.GetPipelineState() == 'Armed':
            self.TrigBase.ResetPipeline()
            self.reset_before_config = False
        self.collection_data_handler.DataHandler.packetCount = 0
        self.collection_data_handler.DataHandler.allcollectiondata = []


        # Pipeline Armed when TrigBase.Configure already called.
        # This if block allows for sequential data streams without reconfiguring the pipeline each time.
        # Reset output data structure before starting data stream again
        if self.TrigBase.GetPipelineState() == 'Armed':
            #self.csv_writer.cleardata()
            for i in range(len(self.channelobjects)):
                self.collection_data_handler.DataHandler.allcollectiondata.append([])
            return True

        # Pipeline Connected when sensors have been scanned in sucessfully.
        # Configure output data using TrigBase.Configure and pass args if you are using a start and/or stop trigger
        elif self.TrigBase.GetPipelineState() == 'Connected':
            #self.csv_writer.clearall()
            self.channelcount = 0
            print("PYDemoTest: Configuring...")
            match self.trigno_station_type:
                case TrignoType.BASESTATION:
                    self.TrigBase.Configure(self.start_trigger, self.stop_trigger)
                case _:
                    self.TrigBase.Configure()
            configured = self.TrigBase.IsPipelineConfigured()
            if configured:
                self.channelobjects = []
                self.plotCount = 0
                self.emgChannelsIdx = []
                globalChannelIdx = 0
                self.channel_guids = []
                for sensor in self.sensors:
                    # CSV Export Config
                    #self.csv_writer.appendSensorHeader(sensor.pair_number, sensor.name)
                    if len(sensor.channels) > 0:
                        print("--Channels")

                        for i in range(len(sensor.channels)):
                            channel = sensor.channels[i]
                            if channel.channel_type == "SkinCheck":
                                continue

                            get_all_channels = True
                            if get_all_channels:
                                self.channel_guids.append(channel.guid)
                                globalChannelIdx += 1

                                #CSV Export Config
                                """
                                if self.collection_data_handler.streamYTData:
                                    self.csv_writer.appendYTChannelHeader(channel.name, channel.sample_rate)
                                    if i == 0:
                                        self.csv_writer.appendSensorHeaderSeperator()
                                    elif i > 0 and i != len(sensor.channels):
                                        self.csv_writer.appendYTSensorHeaderSeperator()
                                else:
                                    self.csv_writer.appendChannelHeader(channel.name, channel.sample_rate)
                                    if i > 0 and i != len(sensor.channels):
                                        self.csv_writer.appendSensorHeaderSeperator()
                                """

                            #NOTE: The self.channel_guids list is used to parse select channels during live data streaming in DataManager.py
                            #      this example will add all available channels to this list (above)
                            #      if you want to only parse certain channels then add only those channel guids to this list
                            #      for example: if you only want the EMG channels during live data streaming (flip bool above to false):
                            if not get_all_channels:
                                if channel.channel_type == 'EMG':
                                    self.channel_guids.append(channel.guid)
                                    #self.csv_writer.h2_channels.append(f"{channel.name} ({str(channel.sample_rate)})")
                                    #if i > 0:
                                    #    self.csv_writer.h1_sensors.append(",")
                                    globalChannelIdx += 1

                            print(f"---- {channel.name} ({str(channel.sample_rate)} Hz) {channel.guid}")
                            self.channelcount += 1
                            self.channelobjects.append(channel)
                            self.collection_data_handler.DataHandler.allcollectiondata.append([])

                            # NOTE: Plotting/Data Output: This demo does not plot non-EMG channel types such as
                            # accelerometer, gyroscope, magnetometer, and others. However, the data from channels
                            # that are excluded from plots are still available via output from PollData()

                            # ---- Plot only EMG Channels
                            if channel.channel_type == 'EMG':
                                self.emgChannelsIdx.append(globalChannelIdx-1)
                                self.plotCount += 1
                if self.collection_data_handler.EMGplot:
                    self.collection_data_handler.EMGplot.initiateCanvas(None, None, self.plotCount, 1, 20000)
                return True
        return False

    def Stop_Callback(self):
        """Callback to stop the data stream"""
        self.collection_data_handler.pauseFlag = True
        self.TrigBase.Stop()
        print("Data Collection Complete")
        #self.csv_writer.data = self.collection_data_handler.DataHandler.allcollectiondata

    # ---------------------------------------------------------------------------------
    # ---- Helper Functions

    def getSampleModes(self, sensorIdx):
        """Gets the list of sample modes available for selected sensor"""
        sampleModes = self.TrigBase.AvailableSensorModes(sensorIdx)
        return sampleModes

    def getCurMode(self, sensorIdx):
        """Gets the current mode of the sensors"""
        if sensorIdx >= 0 and sensorIdx <= len(self.sensors):
            curModes = self.TrigBase.GetCurrentSensorMode(sensorIdx)
            return curModes
        else:
            print("Error: sensor index out of bounds!")
            raise Exception

    def setSampleMode(self, curSensor, setMode):
        """Sets the sample mode for the selected sensor"""
        self.TrigBase.SetSampleMode(curSensor, setMode)
        mode = self.getCurMode(curSensor)
        sensor = self.sensors[curSensor]
        if mode == setMode:
            print(f"({sensor.pair_number}) {sensor.name} - Mode Change Successful")
        else:
            print(f"Error noted when setting sample mode for sensor: ({sensor.pair_number}) {sensor.name}. "
                  f"Tried to set mode to \"{setMode}\". "
                  f"Sensor mode is currently: \"{mode}\"")
        sensor.mode = mode #update the sensor's mode

    def configure_analog_input(self, num_channels: int, is_mic: bool, input_ranges: list, channel_names: list):
        # Only applicable to Trigno Centro receivers
        self.TrigBase.SetAnalogInputConfig(num_channels, is_mic)
        for i in range(num_channels):
            #Input Range values correspond to specific input gains:
            # For DSUB-15 connections: 0 -> 10V, 1 -> 5V, 2 -> 1V, 3 -> 0.1V
            # For Microphone connection: 0 -> 0.09V
            self.TrigBase.SetAnalogInputChannel(i+1, channel_names[i], input_ranges[i])
        self.TrigBase.ApplyAnalogInputSettings()
        self.set_sensors_list()

    def is_ready_to_stream(self):
        return self.TrigBase.IsReadyToStartStream()

    def get_frame_number(self):
        return self.TrigBase.GetFrameCount()

    def get_link_scan_device_options(self, use_ant : bool):
        #use_ant(True) get device types supported in Trigno Link via ANT+ connection
        #use_ant(False) get device types supported in Trigno Link via BLE connection
        return self.TrigBase.GetLinkDeviceNames(use_ant)
