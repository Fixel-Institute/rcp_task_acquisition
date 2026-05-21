import wx
import PySpin
from dataclasses import dataclass
from multiprocessing import Process, Queue

from rcp_task_acquisition.models.Warnings import Warning
from rcp_task_acquisition.utils.file_utils import read_config, write_config
from rcp_task_acquisition.utils.constants import (CAMERA_HEADERS, HEADERS, HARDWARE_LIST,
                            LABJACK_PIN_LIST, ANALOG_RANGES,
                            DELSYS_HEADERS, DELSYS_SENSOR_POSITION_LIST, DELSYS_SENSOR_HEMISPHERE_LIST)
from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./panels/HardwarePanel") 


#keeping track of each row for the hardware/camera selection
#keeping cameras and hardware seperate since we handle them differently in setup and values needed
@dataclass
class HardwareRow:
    name: wx.StaticText
    in_use: wx.CheckBox
    labjack: wx.Choice
    voltage_range: wx.Choice
    in_use_all: bool = False
    in_use_protocol: bool = False


@dataclass
class CameraRow:
    name: wx.StaticText
    in_use: wx.CheckBox
    is_primary: wx.RadioButton
    serial: wx.Choice
    gig_e: wx.CheckBox
    flip_vid: wx.CheckBox
    in_use_all: bool = False
    in_use_protocol: bool = False

@dataclass
class TrignoRow:
    name: wx.StaticText
    in_use: wx.CheckBox
    hemisphere: wx.Choice
    position: wx.Choice
    pair: wx.Button
    in_use_all: bool = False
    in_use_protocol: bool = False

class CamProcess(Process):
    '''
    For some reason the PySpin instance does not like being created on the main thread.
    (it works here and then will cause freezing when trying to run the main gui)
    So our current fix is to put it on its own process
    
    Attributes:
        cam_serial_numbers (list): a list of the cameras that pyspin can currently
                                   access.
    '''
    def __init__(self, cam_queue):
        super().__init__()
        self.cam_queue = cam_queue
    
    def run(self):
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        count = 0
        for camera in cam_list:
            nodemap_tldevice = camera.GetTLDeviceNodeMap()
            node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
            if PySpin.IsReadable(node_device_serial_number):
                logger.debug(node_device_serial_number.GetValue())
                self.cam_queue.put(node_device_serial_number.GetValue())
                count+=1
            camera.DeInit()
            del camera
        self.cam_queue.put("done")
        cam_list.Clear()
        
        system.ReleaseInstance()


class HardwarePanel(wx.Panel):
    '''
    The initial panel where the user can select the hardware and task to run
    
    '''
    def __init__(self, task_config, delsys=None,  parent=None):
        self.args = None
        self.row_list = HARDWARE_LIST
        self.protocol = None
        self.camera_indices = []
        self.hardware_list= []
        self.camera_list = []
        self.trigno_list = []
        self.cam_serial_numbers = []
        self.labjack_selction = LABJACK_PIN_LIST
        self.serial_selections = []
        self.select_protocol = False
        self.user_config = read_config("userdata.yaml")
        self.task_config = task_config
        self.task = None

        self.delsys = delsys
        self.delsys.update_sensors_config_ui = self.update_delsys_config_ui
        self.delsys_refresh_button = None

        self.border = 10
        self.task_list = list(self.task_config.keys())
        
        user_input_count = 1
        while len(self.row_list) < len(LABJACK_PIN_LIST)+1:
            self.row_list.append(f"userInput{user_input_count}")
            user_input_count+=1
            
        super().__init__(parent)
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        vertical_sizer.Add(self._setup_protocol(), 0, wx.EXPAND | wx.ALL, 10)
        vertical_sizer.Add(self._setup_delsys(), 0, wx.EXPAND | wx.ALL, 10 )
        vertical_sizer.Add(self._setup_camera_panel(), 0, wx.EXPAND | wx.ALL, 10)
        vertical_sizer.Add(self._setup_labjack(), 0, wx.EXPAND | wx.ALL, 10 )
        self.SetSizerAndFit(vertical_sizer)

    def _setup_protocol(self):
        self.save_button = wx.Button(self, label="Save Hardware Settings")
        self.save_button.Bind(wx.EVT_BUTTON, self.save_event)
        
        self.hardware_radio = wx.RadioButton(self, label="Update All Hardware", style= wx.RB_GROUP)
        self.hardware_radio.Bind(wx.EVT_RADIOBUTTON, self.hardware_radio_pressed)
        
        self.protocol_radio = wx.RadioButton(self, label="Update Current Protocol")
        self.protocol_radio.Bind(wx.EVT_RADIOBUTTON, self.task_radio_pressed)
        
        grid_sizer = wx.GridBagSizer(6, 1)
        
        grid_sizer.Add(self.hardware_radio, pos=(0,0), span=(0,2), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)   
        grid_sizer.Add(self.protocol_radio, pos=(0,2), span=(0,2), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
        grid_sizer.Add(self.save_button, pos=(0,4), span=(0,2), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
        return grid_sizer

    def _setup_labjack(self):
        hardware_config = self.user_config["hardware"]
        user_input_list = []
        user_input_count = 0
        vertical_pos = 0
        horizontal_pos = 0
        
        labjack_sizer = wx.GridBagSizer(len(HEADERS), len(HARDWARE_LIST))
        for header in HEADERS:
            new_header = wx.StaticText(self, label=header)
            labjack_sizer.Add(new_header, pos=(vertical_pos,horizontal_pos), span=(0,1), flag=wx.ALL, border=self.border)
            horizontal_pos+=1
        vertical_pos+=1
        
        #to get any user added hardware names
        for hardware in hardware_config:
            if hardware not in self.row_list:
                user_input_list.append(hardware)
                
        for hardware in self.row_list:
            in_use = wx.CheckBox(self, id=wx.ID_ANY)
            in_use.Bind(wx.EVT_CHECKBOX, self.update_options)
            
            name = (wx.StaticText(self, label=hardware) 
                    if "user" not in hardware.lower() 
                    else wx.TextCtrl(self, value=hardware))
            name.Enable(False)   
            
            labjack = wx.Choice(self, 
                                id=wx.ID_ANY, 
                                choices=LABJACK_PIN_LIST)
            labjack.Bind(wx.EVT_CHOICE, self._on_choice_labjack)
            labjack.Enable(False)

            
            analog_strings = [str(volt_range) for volt_range in ANALOG_RANGES]
            voltage_ranges = wx.Choice(self, 
                                id=wx.ID_ANY, 
                                choices=analog_strings)
            voltage_ranges.SetSelection(0)
            voltage_ranges.Enable(False)
            voltage_ranges.Hide()
            labjack_sizer.Add(in_use, pos=(vertical_pos,0), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
            labjack_sizer.Add(name, pos=(vertical_pos,1), span=(0,1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=self.border)
            labjack_sizer.Add(labjack, pos=(vertical_pos,2), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
            
            labjack_sizer.Add(voltage_ranges, pos=(vertical_pos,3), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=self.border)
            vertical_pos+=1

            new_hardware = HardwareRow(name, in_use, labjack, voltage_ranges) #min_graph, max_graph, voltage_ranges)
            if hardware in hardware_config.keys():
                labjack.Enable(True)
                name.Enable(True)
                in_use.SetValue(True)
                new_hardware.in_use_all = True
                labjack_value = LABJACK_PIN_LIST.index(hardware_config[hardware]["labjack_input"])
                labjack.SetSelection(labjack_value)
                voltage_ranges.Enable(True)
                if "voltage_range" in hardware_config[hardware].keys() and "A" in hardware_config[hardware]["labjack_input"]:
                    volt_index = ANALOG_RANGES.index(hardware_config[hardware]["voltage_range"][1])
                    voltage_ranges.SetSelection(volt_index)
                    
            elif "user" in hardware.lower() and user_input_count < len(user_input_list):
                voltage_ranges.Enable(True)
                if "voltage_range" in hardware_config[hardware].keys():
                    voltage_ranges.SetSelection(hardware_config[hardware]["voltage_range"])

                labjack.Enable(True)
                name.Enable(True)
                in_use.SetValue(True)
                new_hardware.in_use_all = True
                new_hardware.in_use_all = True
                name.SetValue(user_input_list[user_input_count])
                labjack_value = LABJACK_PIN_LIST.index(hardware_config[user_input_list[user_input_count]]["labjack_input"])
                labjack.SetSelection(labjack_value)
                user_input_count+=1
        
            self.hardware_list.append(new_hardware)
        self._update_lists(self.hardware_list)
        
        labjack_box = wx.StaticBox(self, label="Labjack Setup")
        hardware_sizer = wx.StaticBoxSizer(labjack_box, wx.HORIZONTAL)
        hardware_sizer.Add(labjack_sizer, 1, wx.EXPAND | wx.ALL, 15)
        return hardware_sizer

    def _get_serial_numbers(self):
        cam_queue = Queue()
        camera = CamProcess(cam_queue)
        camera.start()
        while True:
            serial_number = cam_queue.get()
            if serial_number == "done":
                break
            self.cam_serial_numbers.append(serial_number)
        camera.join()
        
    def update_delsys_config_ui(self, status):
        if "IsConnected" in status.keys() and status["IsConnected"]:
            for i in range(len(self.trigno_list)):
                self.trigno_list[i].pair.Enable(True)
            self.delsys_refresh_button.Enable(True)

        if "Sensors" in status.keys():
            for i in range(len(self.trigno_list)):
                self.trigno_list[i].in_use.SetValue(False)
                self.trigno_list[i].name.Enable(False)
                self.trigno_list[i].hemisphere.Enable(False)
                self.trigno_list[i].position.Enable(False)

            for i in range(len(status["Sensors"])):
                sensor_id = status["Sensors"][i]["Id"]-1
                self.trigno_list[sensor_id].in_use.Enable(False)
                self.trigno_list[sensor_id].in_use.SetValue(True)
                self.trigno_list[sensor_id].name.Enable(True)
                self.trigno_list[sensor_id].hemisphere.Enable(True)
                self.trigno_list[sensor_id].position.Enable(True)

    def _setup_delsys(self):
        sensor_list = self.delsys.SensorList

        user_input_list = []
        user_input_count = 0
        vertical_pos = 0
        horizontal_pos = 0

        delsys_sizer = wx.GridBagSizer(len(DELSYS_HEADERS), 18)
        vertical_pos += 1

        for header in DELSYS_HEADERS:
            new_header = wx.StaticText(self, label=header)
            delsys_sizer.Add(new_header, pos=(vertical_pos, horizontal_pos), span=(0, 1), flag=wx.ALL,
                              border=self.border)
            horizontal_pos += 1
        vertical_pos += 1

        for i in range(16):
            in_use = wx.CheckBox(self, id=wx.ID_ANY)
            in_use.Bind(wx.EVT_CHECKBOX, self.update_delsys_sensor)
            in_use.Enable(False)

            name = wx.StaticText(self, label=f"Delsys Sensor #{i + 1}")
            name.Enable(False)

            hemisphere = wx.Choice(self, id=wx.ID_ANY, choices=DELSYS_SENSOR_HEMISPHERE_LIST)
            hemisphere.Bind(wx.EVT_CHOICE, self._on_choice_delsys)
            hemisphere.Enable(False)

            position = wx.Choice(self, id=wx.ID_ANY, choices=DELSYS_SENSOR_POSITION_LIST)
            position.Enable(False)

            pairBtn = wx.Button(self, label="Pair")
            pairBtn.Enable(False)

            delsys_sizer.Add(in_use, pos=(vertical_pos, 0), span=(0, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                              border=self.border)
            delsys_sizer.Add(name, pos=(vertical_pos, 1), span=(0, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL,
                              border=self.border)
            delsys_sizer.Add(hemisphere, pos=(vertical_pos, 2), span=(0, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                              border=self.border)
            delsys_sizer.Add(position, pos=(vertical_pos, 3), span=(0, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                              border=self.border)
            delsys_sizer.Add(pairBtn, pos=(vertical_pos, 4), span=(0, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                             border=self.border)

            vertical_pos += 1

            new_sensor = TrignoRow(name, in_use, hemisphere, position, pair=pairBtn)

            self.trigno_list.append(new_sensor)
        #self._update_lists(self.hardware_list)

        for i in range(len(sensor_list)):
            sensor_id = sensor_list[i]["Id"]-1
            self.trigno_list[sensor_id].in_use.SetValue(True)
            self.trigno_list[sensor_id].name.Enable(True)
            self.trigno_list[sensor_id].hemisphere.Enable(True)
            self.trigno_list[sensor_id].position.Enable(True)
            
            sensor_name = self.trigno_list[sensor_id].name.GetLabel() 
            if sensor_name in self.user_config["delsys"]:
                try:
                    self.trigno_list[sensor_id].hemisphere.SetSelection(DELSYS_SENSOR_HEMISPHERE_LIST.index(self.user_config["delsys"][sensor_name]["hemisphere"])) 
                except:
                    logger.error(f"{sensor_name} is configured for Hemisphere {self.user_config['delsys'][sensor_name]['hemisphere']}, not part of the options.")
                
                try:
                    self.trigno_list[sensor_id].position.SetSelection(DELSYS_SENSOR_POSITION_LIST.index(self.user_config["delsys"][sensor_name]["position"])) 
                except:
                    logger.error(f"{sensor_name} is configured for Hemisphere {self.user_config['delsys'][sensor_name]['hemisphere']}, not part of the options.")

        delsys_box = wx.StaticBox(self, label="Delsys Setup")
        hardware_sizer = wx.StaticBoxSizer(delsys_box, wx.HORIZONTAL)
        hardware_sizer.Add(delsys_sizer, 1, wx.EXPAND | wx.ALL, 15)
        return hardware_sizer

    def _setup_camera_panel(self):
        first_cam = True
        self._get_serial_numbers()
        cam_config = self.user_config["cameras"]
        grid_sizer = wx.GridBagSizer(len(CAMERA_HEADERS), len(self.cam_serial_numbers))
        vertical_pos = 0
        horizontal_pos = 0
        
        for header in CAMERA_HEADERS:
            new_header = wx.StaticText(self, label=header)
            grid_sizer.Add(new_header, pos=(vertical_pos,horizontal_pos), span=(0,1), flag=wx.ALL, border=self.border)
            horizontal_pos+=1
        vertical_pos+=1
       
        for key in cam_config:
            in_use = wx.CheckBox(self, id=wx.ID_ANY)
            in_use.Bind(wx.EVT_CHECKBOX, self.update_options)
            
            name = wx.StaticText(self, label=key)
            name.Enable(False)
            
            serial = wx.Choice(self, choices=self.cam_serial_numbers)
            serial.Bind(wx.EVT_CHOICE, self._on_choice_cameras)
            serial.Enable(False)

            is_primary = (wx.RadioButton(self, style=wx.RB_GROUP) 
                          if first_cam else wx.RadioButton(self))
            
            gig_e = wx.CheckBox(self, id=wx.ID_ANY)
            gig_e.Enable(False)
            
            flip_vid = wx.CheckBox(self, id=wx.ID_ANY)
            flip_vid.Enable(False)
            
            first_cam= False
            is_primary.Enable(False)
            
            new_camera = CameraRow(name, in_use, is_primary, serial, gig_e, flip_vid)
            
            grid_sizer.Add(in_use, pos=(vertical_pos,0), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
            grid_sizer.Add(name, pos=(vertical_pos,1), span=(0,1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
            grid_sizer.Add(is_primary, pos=(vertical_pos,2), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
            grid_sizer.Add(serial, pos=(vertical_pos,3), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
            grid_sizer.Add(gig_e, pos=(vertical_pos, 4), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
            grid_sizer.Add(flip_vid, pos=(vertical_pos, 5), span=(0,1), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
            vertical_pos +=1

            if cam_config[key]["in_use"] and (cam_config[key]["serial"] in self.cam_serial_numbers): 
                new_camera.in_use_all=True
                in_use.SetValue(True)
                name.Enable(True)
                serial.Enable(True)
                is_primary.Enable(True)
                gig_e.Enable(True)
                flip_vid.Enable(True)
                gig_e.SetValue(cam_config[key]["gig_e"])
                is_primary.SetValue(cam_config[key]["ismaster"])
                cam_index = self.cam_serial_numbers.index(cam_config[key]["serial"])
                serial.SetSelection(cam_index)
                flip_vid.SetValue(cam_config[key]["flip"])
            
            self.camera_list.append(new_camera)
        self._update_lists(self.camera_list, is_labjack=False)
        
        camera_box = wx.StaticBox(self, label="Camera Setup")
        camera_sizer = wx.StaticBoxSizer(camera_box, wx.HORIZONTAL)
        camera_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 15)
        
        return camera_sizer

    def hardware_radio_pressed(self, event):
        #update to show active hardware
        self.select_protocol = False
        for hardware in self.hardware_list:
            if hardware.in_use_all:
                hardware.in_use.SetValue(True)
            hardware.in_use.Enable(True)
        for camera in self.camera_list:
            if camera.in_use_all:
                camera.in_use.SetValue(True)
            camera.in_use.Enable(True)
        self.update_options(event)
    
    
    def task_radio_pressed(self, event):
        #update to show available hardware for task
        self.select_protocol = True
        
        for hardware in self.hardware_list:
            if not hardware.in_use.GetValue():
                hardware.in_use.Enable(False)
                hardware.name.Enable(False)
            else:
                hardware.in_use_all = True
                hardware.name.Enable(True)
            hardware.in_use.SetValue(False)
            hardware.voltage_range.Enable(False)
            hardware.labjack.Enable(False)
        for camera in self.camera_list:
            if not camera.in_use.GetValue():
                camera.in_use.Enable(False)
                camera.name.Enable(False)
            else:
                camera.in_use_all = True
                camera.name.Enable(True)

            camera.in_use.SetValue(False)
            camera.serial.Enable(False)
            camera.is_primary.Enable(False)
            camera.gig_e.Enable(False)
            camera.flip_vid.Enable(False)
        
        self.update_task()
        self._update_lists(self.hardware_list)
        self._update_lists(self.camera_list, is_labjack=False)

    def update_delsys_sensor(self, event):
        for sensor in self.trigno_list:
            if sensor.in_use.GetValue():
                sensor.hemisphere.Enable(True)
                sensor.position.Enable(True)
    
    def update_options(self, event):
        for hardware in self.hardware_list:
            if self.hardware_radio.GetValue():
                if hardware.in_use.GetValue():
                    hardware.in_use_all = True
                else:
                    hardware.in_use_all = False
        for camera in self.camera_list:
            if self.hardware_radio.GetValue():
                if camera.in_use.GetValue():
                    camera.in_use_all = True
                else:
                    camera.in_use_all = False
        if not self.select_protocol:
            for hardware in self.hardware_list:
                if hardware.in_use.GetValue():
                    hardware.name.Enable(True)
                    hardware.labjack.Enable(True)
                    hardware.voltage_range.Enable(True)
                else:
                    hardware.name.Enable(False)
                    hardware.labjack.Enable(False)
                    hardware.voltage_range.Enable(False)
                    hardware.labjack.SetSelection(-1)
                    hardware.voltage_range.Hide()
            for camera in self.camera_list:
                if camera.in_use.GetValue():
                    camera.name.Enable(True)
                    camera.is_primary.Enable(True)
                    camera.serial.Enable(True)
                    camera.gig_e.Enable(True)
                    camera.flip_vid.Enable(True)
                    
                else:
                    camera.name.Enable(False)
                    camera.serial.Enable(False)
                    camera.is_primary.Enable(False)
                    camera.gig_e.Enable(False)
                    camera.flip_vid.Enable(False)
                    camera.serial.SetSelection(-1)
            self._update_lists(self.hardware_list)
            self._update_lists(self.camera_list, is_labjack=False)



    def save_event(self, event):
        camera_dict = self._create_camera_dict()
        if not camera_dict:
            return 
        self.user_config["cameras"] = camera_dict
        hardware_dict = self._create_hardware_dict()
        if not hardware_dict:
            Warning("no_hardware").display()
            return
        self.user_config['hardware'] = hardware_dict

        delsys_dict = self._create_delsys_dict()
        if not delsys_dict:
            return
        self.user_config["delsys"] = delsys_dict
        
        if self.select_protocol:
            self.args = []
            
            for hardware in self.hardware_list:
                if hardware.in_use.GetValue():
                    name = self._get_name(hardware)
                    self.args.append(name)
            for camera in self.camera_list:
                if camera.in_use.GetValue():
                    name = self._get_name(camera)
                    self.args.append(name)
            self.task_config[self.task]["settings"] = self.args
            write_config("taskconfig.yaml", self.task_config)
        write_config("userdata.yaml", self.user_config)

    def _create_delsys_dict(self): 
        delsys_dict = {}
        for sensor in self.trigno_list:
            if sensor.in_use.GetValue():
                delsys_dict[sensor.name.GetLabel()] = {
                    "hemisphere": sensor.hemisphere.GetStrings()[sensor.hemisphere.GetSelection()],
                    "position": sensor.position.GetStrings()[sensor.position.GetSelection()]
                }
                
        return delsys_dict

    def _create_hardware_dict(self): 
        hardware_dict = {}
        for hardware in self.hardware_list:
            if hardware.in_use_all:
                labjack_pin = hardware.labjack.GetCurrentSelection()
                if labjack_pin == -1:
                    Warning("hardware").display()
                    return
                name = self._get_name(hardware)
                if not name:
                    Warning("name").display()
                    return
                labjack_list = hardware.labjack.GetStrings()
                labjack_value = labjack_list[labjack_pin]
                voltage_range = [0, 1]
                if "A" in labjack_value:
                    voltage = float(hardware.voltage_range.GetStrings()[hardware.voltage_range.GetCurrentSelection()])
                    voltage_range = [voltage*-1, voltage]
                hardware_dict[name] = {
                        "labjack_input": labjack_value,
                        "voltage_range": voltage_range,
                        "graph": ""
                    }
        return hardware_dict
    
    def _create_camera_dict (self): 
        camera_dict = self.user_config["cameras"]
        for camera in self.camera_list:
            if camera.in_use_all:
                serial = camera.serial.GetCurrentSelection()
                if serial == -1:
                    Warning("serial").display()
                    return
                if self._get_name(camera) in camera_dict.keys():
                    camera_dict[self._get_name(camera)]["ismaster"] = camera.is_primary.GetValue()
                    camera_dict[self._get_name(camera)]["serial"] = camera.serial.GetStrings()[serial]
                    camera_dict[self._get_name(camera)]["in_use"] = camera.in_use_all
                    if camera.gig_e.GetValue():
                        camera_dict[self._get_name(camera)]["framerate"] = int(240/2)
                    else:
                        camera_dict[self._get_name(camera)]["framerate"] = int(240)
                    camera_dict[self._get_name(camera)]["gig_e"] = camera.gig_e.GetValue()
                    camera_dict[self._get_name(camera)]["flip"] = camera.flip_vid.GetValue()
                
                else:
                    camera_dict[self._get_name(camera)] = {"ismaster": camera.is_primary.GetValue(),
                                                            "serial": camera.serial.GetStrings()[serial],
                                                            "in_use": camera.in_use_all,
                                                            "gig_e": camera.gig_e.GetValue(),
                                                            "flip": camera.flip_vid.GetValue()}
                                                                    
            else:
                camera_dict[self._get_name(camera)]["in_use"] = False
                camera_dict[self._get_name(camera)]["ismaster"] = False
                
        return camera_dict
    
    
    def protocol_event(self, event):
        self.args = []
        for hardware in self.hardware_list:
            if hardware.in_use.GetValue():
                name = self._get_name(hardware)
                self.args.append(name)
        for camera in self.camera_list:
            if camera.in_use.GetValue():
                name = self._get_name(camera)
                self.args.append(name)
        self.task_config[self.task]["settings"] = self.args
        write_config("taskconfig.yaml", self.task_config)
        self.update()
        self.close(wx.ID_OK)
    
    
    def _get_name(self, hardware):
        return hardware.name.GetLabel() if hardware.name.GetLabel() != "" else hardware.name.GetValue()
    
    
    def _on_choice_labjack(self, event):
        self._update_lists(self.hardware_list)
        
    def _on_choice_delsys(self, event):
        for i in range(len(self.trigno_list)):
            if self.trigno_list[i].hemisphere.GetSelection() == 2:
                self.trigno_list[i].position.SetSelection(5)
        
    def _on_choice_cameras(self, event):
        self._update_lists(self.camera_list, is_labjack=False)

    def _update_delsys(self, item_list):
        pass
    
    def _update_lists(self, item_list, is_labjack=True):
        selected_list = []
        primary_list = LABJACK_PIN_LIST if is_labjack else self.cam_serial_numbers
        for hardware in item_list:
            choice_list = hardware.labjack if is_labjack else hardware.serial
            if type(choice_list) == wx.Choice and choice_list.GetSelection() !=-1:
                selection = choice_list.GetSelection()
                choices =  choice_list.GetStrings()
                selection = choices[selection]
                original_selection = primary_list.index(selection)
                selected_list.append(original_selection)
        for hardware in item_list:
            choice_list = hardware.labjack if is_labjack else hardware.serial
            try:
                selection = choice_list.GetSelection()
                if selection != -1:
                    choices =  choice_list.GetStrings()
                    selection = choices[selection]
                    original_selection = primary_list.index(selection)
                else:
                    original_selection =-1
                new_options = [hardware for index, hardware in enumerate(primary_list) if index not in selected_list or index == original_selection]

                choice_list.SetItems(new_options)
                if selection !=-1:
                    choice_list.SetSelection(new_options.index(selection))

                    if "A" in primary_list[original_selection]:
                        hardware.voltage_range.Show()
                    else:
                        hardware.voltage_range.Hide()
                    self.Layout()
            except:
                pass
    
    
    def update_task(self):
        if self.task == None:
            for hardware in self.hardware_list:
                hardware.in_use.Enable(False)
                hardware.name.Enable(False)
                hardware.voltage_range.Enable(False)
            for camera in self.camera_list:
                camera.in_use.Enable(False)
                camera.name.Enable(False)
        elif self.select_protocol: 
            for hardware in self.hardware_list:
                name = self._get_name(hardware)
                if name in self.task_config[self.task]["settings"] and hardware.in_use_all:
                    hardware.in_use.SetValue(True)
                    hardware.in_use.Enable(True)
                    hardware.name.Enable(True)
                    hardware.voltage_range.Enable(False)
                else:
                    hardware.in_use.SetValue(False)
            for camera in self.camera_list:
                name = self._get_name(camera)
                if name in self.task_config[self.task]["settings"] and camera.in_use_all:
                    camera.in_use.SetValue(True)
                    camera.in_use.Enable(True)
                    camera.name.Enable(True)
                else:
                    camera.in_use.SetValue(False)
    
    
    def cancel_event(self, event):
        self.close(wx.CANCEL)


    def close(self, value):
        self.dialog.EndModal(value)
        self.dialog.Destroy()


    def show(self):
        return self.dialog.ShowModal()
    
    
    def set_task(self, task):
        self.task = task
        #update to show available hardware for task
        if self.IsShown() and self.protocol_radio.GetValue():
            self.select_protocol = True
            
            for hardware in self.hardware_list:
                if not hardware.in_use_all:
                    hardware.in_use.Enable(False)
                    hardware.name.Enable(False)
                else:
                    hardware.in_use_all = True
                    hardware.name.Enable(True)
                    hardware.in_use.Enable(True)
                hardware.in_use.SetValue(False)
                hardware.labjack.Enable(False)
            for camera in self.camera_list:
                if not camera.in_use_all:
                    camera.in_use.Enable(False)
                    camera.name.Enable(False)
                else:
                    camera.in_use_all = True
                    camera.name.Enable(True)
                    camera.in_use.Enable(True)
                camera.in_use.SetValue(False)
                camera.serial.Enable(False)
                camera.is_primary.Enable(False)
            
            self.update_task()
            self._update_lists(self.hardware_list)
            self._update_lists(self.camera_list, is_labjack=False)


    def reset_hardware(self):
        if not self.hardware_radio.GetValue():
            self.hardware_radio.SetValue(True)
            self.select_protocol = False
            for hardware in self.hardware_list:
                if hardware.in_use_all:
                    hardware.in_use.SetValue(True)
                hardware.in_use.Enable(True)
            for camera in self.camera_list:
                if camera.in_use_all:
                    camera.in_use.SetValue(True)
                camera.in_use.Enable(True)
            self.update_options(None)
            
    
    def get_task(self):
        return self.task
    
    