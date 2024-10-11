from ..datasets import chipset_data
from .. import cpu_identifier
from .. import cpuid
from .. import device_locator
from .. import gpu_identifier
from .. import utils
import time

import wmi

c = wmi.WMI()

class WindowsHardwareInfo:
    def __init__(self):
        self.lookup_codename = cpu_identifier.CPUIdentifier().lookup_codename
        self.classify_gpu = gpu_identifier.GPUIdentifier().classify_gpu
        self.get_device_location_paths = device_locator.WindowsDeviceLocator().get_device_location_paths
        self.utils = utils.Utils()
        self.usb_ids = self.utils.read_file(self.utils.get_full_path("Scripts", "datasets", "usb.ids"))
        self.pci_ids = self.utils.read_file(self.utils.get_full_path("Scripts", "datasets", "pci.ids"))

    def parse_device_path(self, device_path):
        if "VEN" in device_path:
            return {
                "Bus Type": device_path.split("\\")[0],
                "Device ID": "{}-{}".format(device_path.split("VEN_")[-1].split("&")[0], device_path.split("DEV_")[-1].split("&")[0].split("\\")[0])
            }
        
        if "VID" in device_path:
            return {
                "Bus Type": device_path.split("\\")[0],
                "Device ID": "{}-{}".format(device_path.split("VID_")[-1].split("&")[0], device_path.split("PID_")[-1].split("&")[0].split("\\")[0])
            }
        
        if device_path.startswith("HID"):
            device_id = device_path.split("\\")[1].split("&")[0]
            idx = 3 if len(device_id) == 7 else 4
            return {
                "Bus Type": device_path.split("\\")[0],
                "Device ID": "{}-{}".format(device_id[:idx], device_id[idx:]) if len(device_id) < 9 else device_id
            }
        
        return {
            "Bus Type": device_path.split("\\")[0],
            "Device": device_path.split("\\")[1].split("&")[0].split("\\")[0]
        }
    
    def unknown_class_device(self, device_name):
        if self.utils.contains_any(("Video Controller", "Video Adapter", "Graphics Controller"), device_name):
            return "Display"
        
        return None

    def pnp_devices(self):
        self.devices_by_class = {
            "Display": [],
            "Monitor": [],
            "Net": [],
            "MEDIA": [],
            "USB": [],
            "HIDClass": [],
            "Keyboard": [],
            "Mouse": [],
            "HDC": [],
            "SCSIAdapter": [],
            "Biometric": [],
            "Bluetooth": [],
            "SDHost": [],
            "MTD": [],
            "System": []
        }

        for device in c.Win32_PnPEntity():
            device_name = device.Name or "Unknown"
            device_class = device.PNPClass or "Unknown"
            
            if device_class in "Unknown":
                device_class = self.unknown_class_device(device_name) or device_class
            if device_class in "System" and self.utils.contains_any(("LPC ", "eSPI ", "ISA "), device_name):
                self.chipset_device = device
            if device_class in self.devices_by_class:
                self.devices_by_class[device_class].append(device)
            
    def motherboard(self):
        computer_system = c.Win32_ComputerSystem()[0]

        try:
            base_board = c.Win32_BaseBoard()[0]
            system_name = " ".join((base_board.Manufacturer.split()[0], base_board.Product)).upper()
        except:
            system_name = " ".join((computer_system.Manufacturer.split()[0], computer_system.Model)).upper()

        try:
            device_id = self.parse_device_path(self.chipset_device.PNPDeviceID).get("Device ID")

            chipset_model = chipset_data.chipset_controllers[device_id]
        except:
            chipset_model = "Unknown"

        for chipset_name in chipset_data.amd_chipsets:
            if chipset_name in system_name:
                chipset_model = chipset_name
                break

        system_platform = computer_system.PCSystemType
        
        if system_platform == "Unspecified":
            pass
        elif system_platform in (2, 8, 9, 10):
            system_platform = "Laptop"
        else:
            system_platform = "Desktop"
                
        return {
            "Name": system_name,
            "Chipset": chipset_model,
            "Platform": system_platform
        }

    def is_set(self, cpu, leaf, subleaf, reg_idx, bit):
        regs = cpu(leaf, subleaf)

        if (1 << bit) & regs[reg_idx]:
            return True
        
        return False
    
    def get_simd_features(self):
        simd_features_map = {
            "SSE": (1, 0, 3, 25),
            "SSE2": (1, 0, 3, 26),
            "SSE3": (1, 0, 2, 0),
            "SSSE3": (1, 0, 2, 9),
            "SSE4.1": (1, 0, 2, 19),
            "SSE4.2": (1, 0, 2, 20),
            "SSE4a": (0x80000001, 0, 2, 6),
            "AVX": (1, 0, 2, 28),
            "AVX2": (7, 0, 1, 5)
        }

        cpu = cpuid.CPUID()
        simd_feature_support = []

        for feature, address in simd_features_map.items():
            if self.is_set(cpu, *address):
                simd_feature_support.append(feature)

        return ", ".join(simd_feature_support) if simd_feature_support else "SIMD Capabilities Unknown"
    
    def cpu(self):
        cpus = c.Win32_Processor()
   
        cpu_brand = cpus[-1].Manufacturer
        cpu_model = cpus[-1].Name.split("CPU")[0].strip()
        cpu_description = cpus[-1].Description
        number_of_cores = cpus[-1].NumberOfCores or 0

        if "Intel" in cpu_brand:
            cpu_brand = "Intel"
        elif "AMD" in cpu_brand:
            cpu_brand = "AMD"
        
        return {
            "Manufacturer": cpu_brand,
            "Processor Name": cpu_model,
            "Codename": self.lookup_codename(cpu_model, cpu_description),
            "Core Count": str(number_of_cores * len(cpus)).zfill(2),
            "CPU Count": str(len(cpus)).zfill(2),
            "SIMD Features": self.get_simd_features()
        }
       
    def gpu(self):
        gpu_info = {}
        
        for device in self.devices_by_class.get("Display"):
            device_name = device.Name or "Unknown"
            device_class = device.PNPClass or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id or not pnp_device_id.startswith("PCI"):
                continue
            
            device_info = self.classify_gpu(self.parse_device_path(pnp_device_id).get("Device ID"))

            if "Unknown" in (device_name, device_class):
                try:
                    device_name = self.pci_ids.get(device_info.get("Device ID")[:4]).get("devices")[device_info.get("Device ID")[5:]]
                except:
                    pass
            
            device_info.update(self.get_device_location_paths(device))
            gpu_info[self.utils.get_unique_key(device_name, gpu_info)] = device_info

        return dict(sorted(gpu_info.items(), key=lambda item: item[1].get("Device Type", "")))
                        
    def monitor(self):
        monitor_info = {}

        try:
            wmi_service = wmi.WMI(namespace="root\\wmi")

            monitor_ids = sorted(wmi_service.WmiMonitorID(), key=lambda x: x.InstanceName)
            connection_params = sorted(wmi_service.WmiMonitorConnectionParams(), key=lambda x: x.InstanceName)
            source_modes = sorted(wmi_service.WmiMonitorListedSupportedSourceModes(), key=lambda x: x.InstanceName)
            monitor_properties = sorted(self.devices_by_class.get("Monitor"), key=lambda x: x.PNPDeviceID)

            for monitor_id, connection_param, source_modes, monitor_property in zip(monitor_ids, connection_params, source_modes, monitor_properties):
                try:
                    user_friendly_name = monitor_id.UserFriendlyName
                    monitor_name = bytes(user_friendly_name).decode('ascii').rstrip('\x00')
                except:
                    monitor_name = monitor_id.InstanceName.split("\\")[1]
                video_output_type = connection_param.VideoOutputTechnology
                monitor_source_modes = source_modes.MonitorSourceModes

                connected_gpu = None
                parent_device_id = monitor_property.GetDeviceProperties(["DEVPKEY_Device_Parent"])[0][0].Data
                for device in self.devices_by_class.get("Display"):
                    device_name = device.Name or "Unknown"
                    pnp_device_id = device.PNPDeviceID

                    if pnp_device_id and pnp_device_id.startswith("PCI") and pnp_device_id.upper() == parent_device_id.upper():
                        connected_gpu = device_name
                        break
                
                if video_output_type == 0:
                    video_output_type = "VGA"
                elif video_output_type == 4:
                    video_output_type = "DVI"
                elif video_output_type == 5:
                    video_output_type = "HDMI"
                elif video_output_type == 6:
                    video_output_type = "LVDS"
                elif video_output_type == 10:
                    video_output_type = "DP"
                elif video_output_type == 11:
                    video_output_type = "eDP"
                elif video_output_type == -2147483648:
                    video_output_type = "Internal"
                else:
                    video_output_type = "Uninitialized"

                max_h_active = 0
                max_v_active = 0
                
                for monitor_source_mode in monitor_source_modes:
                    max_h_active = max(max_h_active, monitor_source_mode.HorizontalActivePixels)
                    max_v_active = max(max_v_active, monitor_source_mode.VerticalActivePixels)
                
                unique_monitor_name = self.utils.get_unique_key(monitor_name, monitor_info)
                monitor_info[unique_monitor_name] = {
                    "Connector Type": video_output_type,
                    "Resolution": "{}x{}".format(max_h_active, max_v_active)
                }
                if connected_gpu:
                    monitor_info[unique_monitor_name]["Connected GPU"] = connected_gpu
        except:
            pass
        
        return monitor_info
                    
    def network(self):
        network_info = {}

        for device in self.devices_by_class.get("Net"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            
            if device_info.get("Bus Type") == "PCI":
                device_info.update(self.get_device_location_paths(device))
            elif device_info.get("Bus Type") == "USB":
                pass
            else:
                continue
            
            network_info[self.utils.get_unique_key(device_name, network_info)] = device_info

        return network_info
               
    def sound(self):
        sound_info = {}

        for device in self.devices_by_class.get("MEDIA"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            
            if not device_info.get("Bus Type").endswith(("AUDIO", "USB", "ACP")):
                continue
            
            sound_info[self.utils.get_unique_key(device_name, sound_info)] = device_info

        return sound_info
            
    def usb_controllers(self):
        usb_controller_info = {}

        for device in self.devices_by_class.get("USB"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            
            if device_info.get("Bus Type") != "PCI":
                continue
            
            device_info.update(self.get_device_location_paths(device))
            usb_controller_info[self.utils.get_unique_key(device_name, usb_controller_info)] = device_info

        return usb_controller_info
                
    def input(self):
        input_info = {}

        device_type_by_service = {
            "i8042prt": "PS/2",
            "kbdclass": "PS/2",
            "kbdhid": "USB",
            "mouhid": "USB"
        }

        self.devices_by_class["HIDClass"] = sorted(self.devices_by_class.get("HIDClass"), key=lambda item:item.PNPDeviceID.split("\\")[1])
        acpi_device = None
        seen_ids = set()
            
        for device in self.devices_by_class.get("HIDClass") + self.devices_by_class.get("Keyboard") + self.devices_by_class.get("Mouse"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID

            device_info = self.parse_device_path(pnp_device_id)
            
            if device_info.get("Device"):
                idx = 3 if len(device_info.get("Device")) == 7 else 4
                device_info["Device ID"] = device_info["Device"][:idx] + "-" + device_info["Device"][idx:]

            if self.utils.contains_any(("wireless radio controls", "vendor-defined device", "consumer control device", "system controller"), device_name) or device.ConfigManagerErrorCode != 0 or not pnp_device_id:
                continue

            try:
                device_info["Device Type"] = device_type_by_service[device.Service]
            except:
                if device.PNPClass == "Keyboard":
                    device_info["Device Type"] = "Keyboard"
                elif device.PNPClass == "Mouse":
                    device_info["Device Type"] = "Mouse"

            if device.PNPClass == "HIDClass":
                if device_info.get("Bus Type") == "ACPI":
                    acpi_device = {
                        **device_info,
                        "Device Type": device_name
                    }
                    continue
                elif acpi_device and device_info.get("Device ID") == acpi_device.get("Device ID"):
                    device_info.update(acpi_device)

            if device_info.get("Device ID", device_info.get("Device ID")) in seen_ids:
                continue

            try:
                if not device_info.get("Bus Type") in ("ACPI", "USB", "HID") or not device_info.get("Device Type") or device_info.get("Device ID").index("-") > 4:
                    continue
            except:
                continue

            seen_ids.add(device_info.get("Device ID"))

            if not device_info.get("Bus Type") in ("ACPI"):
                try:
                    device_name = self.usb_ids.get(device_info.get("Device ID")[:4]).get("devices")[device_info.get("Device ID")[5:]]
                except:
                    pass
                device_info["Bus Type"] = "USB"
                del device_info["Device Type"]
            else:
                del device_info["Device ID"]

            input_info[self.utils.get_unique_key(device_name, input_info)] = device_info

        return input_info
    
    def storage_controllers(self):
        storage_controller_info = {}

        for device in self.devices_by_class.get("HDC") + self.devices_by_class.get("SCSIAdapter"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            if not device_info.get("Bus Type") in ("PCI", "VID") or " SD " in device_name or "MMC" in device_name:
                continue
            
            device_info.update(self.get_device_location_paths(device))
            storage_controller_info[self.utils.get_unique_key(device_name, storage_controller_info)] = device_info

        return storage_controller_info
        
    def biometric(self):
        biometric_info = {}

        for device in self.devices_by_class.get("Biometric"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            if device_info.get("Bus Type") in ("ROOT", "USB"):
                biometric_info[self.utils.get_unique_key(device_name, biometric_info)] = device_info

        return biometric_info
        
    def bluetooth(self):
        bluetooth_info = {}
        
        for device in self.devices_by_class.get("Bluetooth"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            if device_info.get("Bus Type") in "USB":
                bluetooth_info[self.utils.get_unique_key(device_name, bluetooth_info)] = device_info

        return bluetooth_info
                 
    def sd_controller(self):
        sd_controller_info = {}

        for device in self.devices_by_class.get("SDHost") + self.devices_by_class.get("MTD"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            sd_controller_info[self.utils.get_unique_key(device_name, sd_controller_info)] = device_info
        
        return sd_controller_info
        
    def system_devices(self):
        system_device_info = {}

        for device in self.devices_by_class.get("System"):
            device_name = device.Name or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id:
                continue
                            
            device_info = self.parse_device_path(pnp_device_id)
            device_info.update(self.get_device_location_paths(device))
            system_device_info[self.utils.get_unique_key(device_name, system_device_info)] = device_info

        return system_device_info

    def hardware_collector(self):
        self.utils.head("Hardware Information Collection")
        print("")
        print("Please wait while we gather your hardware details")
        print("")
        self.result = {}

        steps = [
            ('Gathering PnP devices', self.pnp_devices, None),
            ('Gathering motherboard information', self.motherboard, "Motherboard"),
            ('Gathering CPU information', self.cpu, "CPU"),
            ('Gathering GPU information', self.gpu, "GPU"),
            ('Gathering monitor information', self.monitor, "Monitor"),
            ('Gathering network information', self.network, "Network"),
            ('Gathering sound information', self.sound, "Sound"),
            ('Gathering USB controllers', self.usb_controllers, "USB Controllers"),
            ('Gathering input devices', self.input, "Input"),
            ('Gathering storage controllers', self.storage_controllers, "Storage Controllers"),
            ('Gathering biometric information', self.biometric, "Biometric"),
            ('Gathering bluetooth information', self.bluetooth, "Bluetooth"),
            ('Gathering sd controller information', self.sd_controller, "SD Controller"),
            ('Gathering system devices', self.system_devices, "System Devices")
        ]

        total_steps = len(steps)
        for index, (message, function, attribute) in enumerate(steps, start=1):
            print(f"[{index}/{total_steps}] {message}...")
            value = function()
            if not attribute:
                continue
            if value:
                self.result[attribute] = value
            else:
                print("    - No {} found.".format(attribute.lower()))

        print("")
        print("Hardware information collection complete.")
        time.sleep(1)