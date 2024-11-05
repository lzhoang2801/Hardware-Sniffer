from ..datasets import chipset_data
from .. import cpu_identifier
from .. import cpuid
from .. import device_locator
from .. import gpu_identifier
from .. import utils
import time
import re
import wmi
import winreg

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
        device_info = {}
        
        parts = device_path.split("\\")
        
        device_info["Bus Type"] = parts[0]
        
        if "&" not in parts[1]:
            device_info["Device"] = parts[1]
            return device_info

        vendor_id, device_id, product_id, hid_id, subsystem_id = None, None, None, None, None
    
        for segment in parts[1].replace("_", "").split("&"):
            if segment.startswith("VEN"):
                vendor_id = segment.split("VEN")[-1].zfill(4)
            elif segment.startswith("DEV"):
                device_id = segment.split("DEV")[-1]
            elif segment.startswith("VID"):
                vendor_id = segment.split("VID")[-1].zfill(4)
            elif segment.startswith("PID"):
                product_id = segment.split("PID")[-1]
            elif segment.startswith("HID"):
                hid_id = segment.split("HID")[-1]
            elif segment.startswith("SUBSYS"):
                subsystem_id = segment.split("SUBSYS")[-1]
        
        if vendor_id and device_id or product_id or hid_id:
            device_info["Device ID"] = "{}-{}".format(vendor_id, device_id or product_id or hid_id)

        if subsystem_id:
            device_info["Subsystem ID"] = subsystem_id
        
        return device_info
    
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
        manufacturer = model = "Unknown"

        try:
            base_board = c.Win32_BaseBoard()[0]
            manufacturer = base_board.Manufacturer
            model = base_board.Product
        except: pass

        try:
            computer_system = c.Win32_ComputerSystem()[0]
            manufacturer = computer_system.Manufacturer
            model = computer_system.Model
        except: pass

        manufacturer = manufacturer.split(" ")[0]
        system_name = (" ".join(item for item in (manufacturer, model) if not "unknown" in item.lower()) or model).upper()

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

        registry_path = r"SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        resize_bar_status = {}

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as base_key:
                index = 0
                
                while True:
                    try:
                        subkey_name = winreg.EnumKey(base_key, index)
                        index += 1
                        subkey_path = f"{registry_path}\\{subkey_name}"

                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path) as gpu_key:
                            is_resize_bar_enabled = False
                            value_index = 0

                            while True:
                                try:
                                    reg_key, value, reg_type = winreg.EnumValue(gpu_key, value_index)
                                    value_index += 1

                                    if reg_key == "KMD_RebarControlMode" and value == 1:
                                        is_resize_bar_enabled = True
                                    elif reg_key == "MatchingDeviceId":
                                        pnp_device_id = value.upper()
                                except OSError:
                                    break
                            
                            if resize_bar_status.get(pnp_device_id, False) == True:
                                continue
                            
                            resize_bar_status[pnp_device_id] = is_resize_bar_enabled
                    except OSError:
                        break
        except FileNotFoundError:
            pass
        except Exception as e:
            pass

        for device in self.devices_by_class.get("Display"):
            device_name = device.Name or "Unknown"
            device_class = device.PNPClass or "Unknown"
            pnp_device_id = device.PNPDeviceID
            
            if not pnp_device_id or not pnp_device_id.startswith("PCI"):
                continue
            
            device_info = self.parse_device_path(pnp_device_id)
            del device_info["Bus Type"]
            device_info = {**self.classify_gpu(device_info.get("Device ID")), **device_info}

            if "Unknown" in (device_name, device_class):
                try:
                    device_name = self.pci_ids.get(device_info.get("Device ID")[:4]).get("devices")[device_info.get("Device ID")[5:]]
                except:
                    pass
            
            device_info.update(self.get_device_location_paths(device))

            def extract_key_parts(device_id):
                match = re.search(r"VEN_(\w+)&DEV_(\w+)", device_id)
                return match.groups() if match else None
            
            for gpu_id, resize_bar_enabled in resize_bar_status.items():
                gpu_parts = extract_key_parts(gpu_id)
                pnp_parts = extract_key_parts(pnp_device_id)

                if gpu_parts and pnp_parts and gpu_parts == pnp_parts:
                    device_info["Resizable BAR"] = "Enabled" if resize_bar_enabled else "Disabled"

            gpu_info[self.utils.get_unique_key(device_name, gpu_info)] = device_info

        return dict(sorted(gpu_info.items(), key=lambda item: item[1].get("Device Type", "")))
                        
    def monitor(self):
        monitor_info = {}

        monitor_properties = self.devices_by_class.get("Monitor")

        try:
            wmi_service = wmi.WMI(namespace="root\\wmi")

            monitor_ids = wmi_service.WmiMonitorID()
            connection_params = wmi_service.WmiMonitorConnectionParams()
            source_modes = wmi_service.WmiMonitorListedSupportedSourceModes()
        except:
            monitor_ids = connection_params = source_modes = []

        for monitor_property in monitor_properties:
            try:
                monitor_id = next((monitor_id for monitor_id in monitor_ids if monitor_property.PNPDeviceID in monitor_id.InstanceName.upper()), None)
                user_friendly_name = monitor_id.UserFriendlyName
                monitor_name = bytes(user_friendly_name).decode('ascii').rstrip('\x00')
            except:
                monitor_name = monitor_property.PNPDeviceID.split("\\")[1]
            
            try:
                connection_param = next((connection_param for connection_param in connection_params if monitor_property.PNPDeviceID in connection_param.InstanceName.upper()), None)
                video_output_type = connection_param.VideoOutputTechnology

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
            except:
                video_output_type = "Uninitialized"

            max_h_active = 0
            max_v_active = 0

            try:
                source_mode = next((source_mode for source_mode in source_modes if monitor_property.PNPDeviceID in source_mode.InstanceName.upper()), None)
                monitor_source_modes = source_mode.MonitorSourceModes

                for monitor_source_mode in monitor_source_modes:
                    max_h_active = max(max_h_active, monitor_source_mode.HorizontalActivePixels)
                    max_v_active = max(max_v_active, monitor_source_mode.VerticalActivePixels)
            except:
                pass

            connected_gpu = None
            parent_device_id = monitor_property.GetDeviceProperties(["DEVPKEY_Device_Parent"])[0][0].Data
            for device in self.devices_by_class.get("Display"):
                device_name = device.Name or "Unknown"
                pnp_device_id = device.PNPDeviceID

                if pnp_device_id and pnp_device_id.startswith("PCI") and pnp_device_id.upper() == parent_device_id.upper():
                    connected_gpu = device_name
                    break
            
            unique_monitor_name = self.utils.get_unique_key(monitor_name, monitor_info)
            monitor_info[unique_monitor_name] = {
                "Connector Type": video_output_type,
                "Resolution": "{}x{}".format(max_h_active, max_v_active)
            }
            if connected_gpu:
                monitor_info[unique_monitor_name]["Connected GPU"] = connected_gpu

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

            try:
                device_name = self.pci_ids.get(device_info.get("Device ID")[:4]).get("devices")[device_info.get("Device ID")[5:]]
            except:
                pass
            
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