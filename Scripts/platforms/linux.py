from ..datasets import chipset_data
from .. import cpu_identifier
from .. import device_locator
from .. import gpu_identifier
from .. import run
from .. import utils
import time
import os
import re

PCI_DEVICES_PATH = "/sys/bus/pci/devices"
USB_DEVICES_PATH = "/sys/bus/usb/devices"

class LinuxHardwareInfo:
    def __init__(self):
        self.lookup_codename = cpu_identifier.CPUIdentifier().lookup_codename
        self.classify_gpu = gpu_identifier.GPUIdentifier().classify_gpu
        self.get_device_location_paths = device_locator.LinuxDeviceLocator().get_device_location_paths
        self.run = run.Run().run
        self.utils = utils.Utils()
    
        
    def _read_sys_file(self, path):
            content_bytes = self.utils.read_file(path)
            if content_bytes:
                return content_bytes.decode('utf-8', errors='ignore').strip()
            return ""

    def format_value(self, value, type="string"):
        if not value:
            return None
        
        value = value.strip()

        try:
            if type == "int":
                return int(value)
        except:
            return None
        
        return value
    
    def get_pci_device_name_and_class(self, device_slot_name):
        output = self.run({
            "args": ["lspci", "-vmm", "-s", device_slot_name]
        })

        if output[2] != 0:
            return "Unknown", "Unknown"

        device_class = vendor_name = device_name = None

        for line in output[0].splitlines():
            lower_line = line.lower()

            if "class" in lower_line:
                device_class = line.split(":")[-1].strip()
            elif "vendor" in lower_line:
                vendor_name = line.split(":")[-1].strip()
            elif "device" in lower_line:
                device_name = line.split(":")[-1].strip()

            if all((device_class, device_name)):
                break

        device_name = " ".join((name for name in (vendor_name, device_name) if name))

        if not device_name:
            device_name = "Unknown"

        if not device_class:
            device_class = "Unknown"
        else:
            device_class = device_class.split("[")[0].strip()

        return device_name, device_class

    def get_usb_device_name_and_class(self, vendor_id, device_id):
        output = self.run({
            "args": ["lsusb", "-v", "-d", "{}:{}".format(vendor_id, device_id)]
        })

        if output[2] != 0:
            return "Unknown", "Unknown"

        device_class = vendor_name = product_name = None

        for line in output[0].splitlines():
            lower_line = line.lower()
            value = " ".join(line.split()[2:]).strip()

            if not value:
                continue

            if "bdeviceprotocol" in lower_line:
                device_class = value
            elif "idvendor" in lower_line:
                vendor_name = value
            elif "idproduct" in lower_line:
                product_name = value
            elif "iproduct" in lower_line:
                product_name = value

        device_name = " ".join((name for name in (vendor_name, product_name) if name))

        if not device_name:
            device_name = "Unknown"
        if not device_class:
            device_class = "Unknown"

        return device_name, device_class       

    def pci_devices(self):
        self.devices_by_class = {}
        self.chipset_model = "Unknown"

        pci_devices_data = {}

        if not os.path.exists(PCI_DEVICES_PATH):
            return pci_devices_data
        
        for device_slot_name in os.listdir(PCI_DEVICES_PATH):
            device_dir = os.path.join(PCI_DEVICES_PATH, device_slot_name)

            if not os.path.exists(device_dir):
                continue

            device_name, device_class = self.get_pci_device_name_and_class(device_slot_name)

            if device_class in ("Network controller", "Display controller", "VGA compatible controller", "3D controller"):
                continue

            vendor_id = self._read_sys_file(os.path.join(device_dir, "vendor"))
            device_id = self._read_sys_file(os.path.join(device_dir, "device"))
            subsystem_vendor_id = self._read_sys_file(os.path.join(device_dir, "subsystem_vendor"))
            subsystem_device_id = self._read_sys_file(os.path.join(device_dir, "subsystem_device"))

            if not all((device_name, vendor_id, device_id)):
                continue

            device_info = {
                "Name": device_name,
                "Device Path": device_slot_name,
                "Bus Type": "PCI",
                "Device ID": "{}-{}".format(vendor_id[2:], device_id[2:]).upper()
            }

            if all((subsystem_vendor_id, subsystem_device_id)):
                device_info["Subsystem ID"] = "{}{}".format(subsystem_device_id[2:], subsystem_vendor_id[2:]).upper()

            device_info.update(self.get_device_location_paths(device_dir))

            if not device_class in self.devices_by_class:
                self.devices_by_class[device_class] = []
                
            self.devices_by_class[device_class].append(device_info)

        return pci_devices_data
          
    def motherboard(self):
        manufacturer = self._read_sys_file("/sys/class/dmi/id/sys_vendor").split(" ")[0]
        model = self._read_sys_file("/sys/class/dmi/id/product_name")

        board_manufacturer = self._read_sys_file("/sys/class/dmi/id/board_vendor").split(" ")[0]
        board_model = self._read_sys_file("/sys/class/dmi/id/board_name")

        for prefix in ("unknown", "manufacturer", "o.e.m.", "product"):
            if prefix in board_manufacturer.lower():
                board_manufacturer = ""
            if prefix in board_model.lower():
                board_model = ""
            if prefix in manufacturer.lower():
                manufacturer = board_manufacturer
            if prefix in model.lower():
                model = board_model

        if len(manufacturer) < len(board_manufacturer):
            manufacturer = board_manufacturer

        if len(model) < len(board_model):
            model = board_model

        if manufacturer == model and model == "":
            system_name = "Unknown"
        else:
            system_name = " ".join([manufacturer, model]).strip().upper()

        chipset_model = "Unknown"

        for device in self.devices_by_class.get("ISA bridge", []):
            if device.get("Device ID") in chipset_data.chipset_controllers:
                chipset_model = chipset_data.chipset_controllers[device.get("Device ID")]
                break

        for chipset_name in chipset_data.amd_chipsets:
            if chipset_name in system_name:
                chipset_model = chipset_name
                break

        system_platform = self._read_sys_file("/sys/class/dmi/id/chassis_type") or "Unspecified"

        try:
            system_platform = int(system_platform)

            if system_platform in (2, 8, 9, 10):
                system_platform = "Laptop"
            else:
                system_platform = "Desktop"
        except:
            system_platform = "Unspecified"
                
        return {
            "Name": system_name,
            "Chipset": chipset_model,
            "Platform": system_platform
        }

    def bios(self):
        bios_info = {}

        bios_info["Version"] = self._read_sys_file("/sys/class/dmi/id/bios_version") or "Unknown"
        bios_info["Release Date"] = self._read_sys_file("/sys/class/dmi/id/bios_date") or "Unknown"

        if os.path.exists("/sys/firmware/efi"):
            bios_info["Firmware Type"] = "UEFI"
        else:
            bios_info["Firmware Type"] = "BIOS"

            
        try:
            secure_boot_val = self._read_sys_file("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c")
            bios_info["Secure Boot"] = "Enabled" if secure_boot_val else "Disabled"
        except Exception:
            bios_info["Secure Boot"] = "Disabled"

  
        bios_info["Above 4G Decoding"] = "Disabled"

        for class_name in self.devices_by_class:
            for device in self.devices_by_class[class_name]:
                if device.get("Device Path"):
                    device_dir = os.path.join(PCI_DEVICES_PATH, device.get("Device Path"))

                    if os.path.exists(device_dir):
                        for resource_path, _ in self.utils.find_matching_paths(device_dir, name_filter="resource", type_filter="file"):
                            try:
                                resource = self._read_sys_file(os.path.join(device_dir, resource_path))

                                for line in resource.splitlines():
                                    line = line.strip()

                                    start_address, end_address, flags = line.split()[0:3]

                                    if int(end_address, 16) >= 2**32:
                                        bios_info["Above 4G Decoding"] = "Enabled"
                            except:
                                continue

        return bios_info
    
    def get_simd_features(self, flags):
        simd_features_required = ["SSE", "SSE2", "SSE3", "SSSE3", "SSE4.1", "SSE4.2", "SSE4a", "AVX", "AVX2"]
        simd_feature_support = []

        for feature in simd_features_required:
            if feature.lower().replace(".", "_") in flags:
                simd_feature_support.append(feature)

        return ", ".join(simd_feature_support) if simd_feature_support else "SIMD Capabilities Unknown"
    
    def cpu(self):
        cpu_info_str = self._read_sys_file("/proc/cpuinfo")
        cpu_cores = cpu_info_str.split("\n\n") if cpu_info_str else []

        if not cpu_cores or not cpu_cores[0].strip():
            return None

        first_core_info = cpu_cores[0]
        
        cpu_brand = cpu_model = cpu_family = model = stepping = flags = None
        
        for line in first_core_info.splitlines():
            if ":" in line:
                try:
                    key, value = [x.strip() for x in line.split(":", 1)]
                    if key == "vendor_id":
                        cpu_brand = value
                    elif key == "cpu family":
                        cpu_family = value
                    elif key == "model name":
                        # Clean up the model name string
                        cpu_model = value.split("with")[0].split("@")[0].replace(" CPU", "").strip()
                    elif key == "model":
                        model = value
                    elif key == "stepping":
                        stepping = value
                    elif key == "flags":
                        flags = value
                except (ValueError, IndexError):
                    continue
        
        if not all((cpu_brand, cpu_family, model, cpu_model, stepping, flags)):
            return None

        number_of_cores = len([core for core in cpu_cores if core.strip()])
        physical_ids = {line.split(":")[-1].strip() for core in cpu_cores for line in core.splitlines() if "physical id" in line}
        cpu_count = len(physical_ids) if physical_ids else 1

        cpu_description = f"Family {cpu_family} Model {model} Stepping {stepping}"

        if "Intel" in cpu_brand:
            cpu_brand = "Intel"
        elif "AMD" in cpu_brand:
            cpu_brand = "AMD"
        
        return {
            "Manufacturer": cpu_brand,
            "Processor Name": cpu_model,
            "Codename": self.lookup_codename(cpu_model, cpu_description),
            "Core Count": str(number_of_cores).zfill(2),
            "CPU Count": str(cpu_count).zfill(2),
            "SIMD Features": self.get_simd_features(flags)
        }
       
    def gpu(self):
        gpu_info = {}

        DRM_DEVICES_PATH = "/sys/class/drm"

        if not os.path.exists(DRM_DEVICES_PATH):
            return gpu_info
        
        graphics_devices = self.utils.find_matching_paths(DRM_DEVICES_PATH, name_filter="card", type_filter="dir")

        for graphics_device, _ in graphics_devices:
            if "-" in graphics_device:
                continue

            device_dir = os.path.join(DRM_DEVICES_PATH, graphics_device)
            uevent = self._read_sys_file(os.path.join(device_dir, "device", "uevent"))

            if not uevent:
                continue

            vendor_id = device_id = subsystem_vendor_id = subsystem_device_id = device_slot_name = bus_type = None

            for line in uevent.splitlines():
                lower_line = line.lower()

                if "pci_id" in lower_line:
                    vendor_id, device_id = line.split("=")[-1].split(":")

                    vendor_id = vendor_id.zfill(4)
                    device_id = device_id.zfill(4)
                elif "pci_subsys_id" in lower_line:
                    subsystem_vendor_id, subsystem_device_id = line.split("=")[-1].split(":")

                    subsystem_vendor_id = subsystem_vendor_id.zfill(4)
                    subsystem_device_id = subsystem_device_id.zfill(4)
                elif "pci_slot_name" in lower_line:
                    device_slot_name = line.split("=")[-1]
                elif "modalias" in lower_line:
                    bus_type = line.split("=")[-1].split(":")[0].upper()

            if not all((bus_type, vendor_id, device_id)):
                continue

            device_name, device_class = self.get_pci_device_name_and_class(device_slot_name)

            device_info = {
                "Bus Type": bus_type,
                "Device ID": "{}-{}".format(vendor_id, device_id).upper()
            }

            device_info.update(self.classify_gpu(device_info["Device ID"]))

            if all((subsystem_vendor_id, subsystem_device_id)):
                device_info["Subsystem ID"] = "{}{}".format(subsystem_device_id, subsystem_vendor_id).upper()
            
            device_dir = os.path.join(device_dir, "device")
            device_info.update(self.get_device_location_paths(device_dir))

            device_info["Resizable BAR"] = "Disabled"

            if os.path.exists(device_dir):
                for resource_path, _ in self.utils.find_matching_paths(device_dir, name_filter="resource", type_filter="file"):
                    try:
                        resource = self.utils.read_file(os.path.join(device_dir, resource_path))
                        parts = resource.split()

                        for index in range(0, len(parts), 3):
                            start_address, end_address, flags = parts[index:index + 3]

                            start_address = int(start_address, 16)
                            end_address = int(end_address, 16)
                            memory_size = end_address - start_address + 1

                            if memory_size >= 2**32:
                                device_info["Resizable BAR"] = "Enabled"
                    except:
                        continue

            device_info["Device Path"] = device_dir

            gpu_info[self.utils.get_unique_key(device_name, gpu_info)] = device_info

        return dict(sorted(gpu_info.items(), key=lambda item: item[1].get("Device Type", "")))
    
    def decode_manufacturer_id(self, manufacturer_bytes):
        if len(manufacturer_bytes) != 2:
            return None

        manufacturer_int = int.from_bytes(manufacturer_bytes, 'big')

        char1 = (manufacturer_int >> 10) & 0x1F
        char2 = (manufacturer_int >> 5) & 0x1F
        char3 = manufacturer_int & 0x1F

        def to_char(value):
            if 1 <= value <= 26:
                return chr(value + ord('A') - 1)
            else:
                return None

        c1 = to_char(char1)
        c2 = to_char(char2)
        c3 = to_char(char3)

        if not all((c1, c2, c3)):
            return None

        return c1 + c2 + c3
    
    def parse_edid(self, edid_bytes):
        edid_data = {}

        if len(edid_bytes) < 128:
            return edid_data
        
        try:
            header = edid_bytes[0:8]
            edid_data['header'] = header.hex()

            manufacturer_id = self.decode_manufacturer_id(edid_bytes[8:10])
            edid_data['manufacturer_id'] = manufacturer_id
            
            product_code = edid_bytes[10:12][::-1]
            edid_data['product_code'] = product_code.hex().upper()

            serial_number = edid_bytes[12:16]
            edid_data['serial_number'] = int.from_bytes(serial_number, 'little')

            week_of_manufacture = edid_bytes[16]
            edid_data['week_of_manufacture'] = week_of_manufacture

            year_of_manufacture = edid_bytes[17] + 1990
            edid_data['year_of_manufacture'] = year_of_manufacture

            edid_version = edid_bytes[18:20]
            edid_data['edid_version'] = f"{edid_version[0]}.{edid_version[1]}"

            basic_display_params = edid_bytes[20:25]
            edid_data['basic_display_params'] = basic_display_params.hex()

            chroma_data = edid_bytes[25:35]
            edid_data['chroma_data'] = chroma_data.hex()

            established_timings = edid_bytes[35:38]
            edid_data['established_timings'] = established_timings.hex()

            standard_timings = edid_bytes[38:54]
            edid_data['standard_timings'] = standard_timings.hex()

            descriptor_blocks = edid_bytes[54:126]
            edid_data['descriptor_blocks'] = descriptor_blocks.hex()

            checksum = edid_bytes[127]
            edid_data['checksum'] = checksum

            checksum_calc = 256 - (sum(edid_bytes[:127]) % 256)
            edid_data['checksum_valid'] = (checksum == checksum_calc)

            if len(edid_bytes) > 128:
                extension_blocks = edid_bytes[128:]
                edid_data['extension_blocks'] = extension_blocks.hex()
        except:
            pass

        return edid_data
                        
    def monitor(self):
        monitor_info = {}

        for gpu_name, gpu_info in self.result.get("GPU", {}).items():
            gpu_dir = gpu_info.get("Device Path")
            del gpu_info["Device Path"]

            if os.path.exists(gpu_dir):
                for edid_path, _ in self.utils.find_matching_paths(gpu_dir, name_filter="edid", type_filter="file"):
                    monitor_name = "Unknown"

                    edid_parsed = self.parse_edid(self.utils.read_file(os.path.join(gpu_dir, edid_path)))

                    if all((edid_parsed.get("manufacturer_id"), edid_parsed.get("product_code"))):
                        monitor_name = "{}{}".format(edid_parsed.get("manufacturer_id"), edid_parsed.get("product_code"))

                    connected = False
                    max_h_active = 0
                    max_v_active = 0            

                    monitor_dir = os.path.join(gpu_dir, os.path.dirname(edid_path))
                    
                    status_str = self._read_sys_file(os.path.join(monitor_dir, "status"))
                    connected = "connected" == status_str
                            
                    if not connected:
                        continue
                    
                    modes_str = self._read_sys_file(os.path.join(monitor_dir, "modes"))
                    for mode in modes_str.splitlines():
                                try:
                                    h_active, v_active = map(int, mode.split("x"))

                                    max_h_active = max(max_h_active, h_active)
                                    max_v_active = max(max_v_active, v_active)
                                except:
                                    continue

                    if not connected:
                        continue

                    max_resolution = "{}x{}".format(max_h_active, max_v_active)

                    try:
                        connector_type = "-".join(os.path.basename(os.path.dirname(edid_path)).split("-")[1:-1])
                    except:
                        connector_type = "Uninitialized"

                    monitor_info[self.utils.get_unique_key(monitor_name, monitor_info)] = {
                        "Connector Type": connector_type,
                        "Max Resolution": max_resolution,
                        "Connected GPU": gpu_name
                    }

        return monitor_info
                    
    def network(self):
        network_info = {}

        NET_DEVICES_PATH = "/sys/class/net"

        if not os.path.exists(NET_DEVICES_PATH):
            return network_info
        
        for device in os.listdir(NET_DEVICES_PATH):
            device_dir = os.path.join(NET_DEVICES_PATH, device)
            uevent = self._read_sys_file(os.path.join(device_dir, "device", "uevent"))

            if not uevent:
                continue

            vendor_id = device_id = subsystem_vendor_id = subsystem_device_id = device_slot_name = bus_type = None

            for line in uevent.splitlines():
                lower_line = line.lower()

                if "pci_id" in lower_line:
                    vendor_id, device_id = line.split("=")[-1].split(":")

                    vendor_id = vendor_id.zfill(4)
                    device_id = device_id.zfill(4)
                elif "pci_subsys_id" in lower_line:
                    subsystem_vendor_id, subsystem_device_id = line.split("=")[-1].split(":")

                    subsystem_vendor_id = subsystem_vendor_id.zfill(4)
                    subsystem_device_id = subsystem_device_id.zfill(4)
                elif "pci_slot_name" in lower_line:
                    device_slot_name = line.split("=")[-1]
                elif "modalias" in lower_line:
                    bus_type = line.split("=")[-1].split(":")[0].upper()

            if not all((vendor_id, device_id)):
                continue

            device_name, device_class = self.get_pci_device_name_and_class(device_slot_name)

            device_info = {
                "Bus Type": bus_type,
                "Device ID": "{}-{}".format(vendor_id, device_id).upper()
            }

            if all((subsystem_vendor_id, subsystem_device_id)):
                device_info["Subsystem ID"] = "{}{}".format(subsystem_device_id, subsystem_vendor_id).upper()

            device_info.update(self.get_device_location_paths(device_dir))

            network_info[self.utils.get_unique_key(device_name, network_info)] = device_info

        return network_info
    
    def sound(self):
        sound_info = {}

        SOUND_DEVICES_PATH = "/sys/class/sound"

        if not os.path.exists(SOUND_DEVICES_PATH):
            return sound_info
        
        sound_cards = self.utils.find_matching_paths(SOUND_DEVICES_PATH, name_filter="card", type_filter="dir")

        for sound_card, _ in sound_cards:
            device_dir = os.path.join(SOUND_DEVICES_PATH, sound_card, "device")

            vendor_id = device_id = None

            for property_name in os.listdir(device_dir):
                card_property_path = os.path.join(device_dir, property_name)

                if property_name == "vendor":
                    vendor_id = self.format_value(self.utils.read_file(card_property_path))
                elif property_name == "device":
                    device_id = self.format_value(self.utils.read_file(card_property_path))

            if not all((vendor_id, device_id)):
                continue
            
            card_device_id = "{}-{}".format(vendor_id[2:], device_id[2:]).upper()

            sound_device_dirs = self.utils.find_matching_paths(device_dir, name_filter="hdaudio", type_filter="dir")

            for sound_device_dir, _ in sound_device_dirs:
                codec_name = "Unknown"
                codec_id = subsystem_id = bus_type = None

                codec_name = self._read_sys_file(os.path.join(device_dir, sound_device_dir, "chip_name"))
                codec_vendor = self._read_sys_file(os.path.join(device_dir, sound_device_dir, "vendor_name"))
                codec_id_str = self._read_sys_file(os.path.join(device_dir, sound_device_dir, "vendor_id"))
                subsystem_id = self._read_sys_file(os.path.join(device_dir, sound_device_dir, "subsystem_id"))
                bus_type_str = self._read_sys_file(os.path.join(device_dir, sound_device_dir, "modalias"))

                if codec_id_str:
                    codec_id = codec_id_str[2:].upper()
                    codec_id = f"{codec_id[:4]}-{codec_id[4:]}"
                else:
                    codec_id = None
                
                if subsystem_id:
                    subsystem_id = subsystem_id[2:].upper()

                if bus_type_str:
                    bus_type = bus_type_str.split(":")[0].upper()
                else:
                    bus_type = None

                if all((codec_vendor, codec_name)):
                    codec_name = "{} {}".format(codec_vendor, codec_name)

                if all((codec_id, subsystem_id)):
                    codec_info = {
                        "Bus Type": bus_type,
                        "Device ID": codec_id,
                        "Subsystem ID": subsystem_id,
                        "Controller Device ID": card_device_id
                    }

                    sound_info[self.utils.get_unique_key(codec_name, sound_info)] = codec_info

        return sound_info

    def usb_controllers(self):
        usb_controller_info = {}

        for device in self.devices_by_class.get("USB controller", []):
            device_name = device.get("Name", "Unknown")
            device_dir = os.path.join(PCI_DEVICES_PATH, device.get("Device Path"))

            if not os.path.exists(device_dir):
                continue

            controller_info = {
                "Bus Type": device.get("Bus Type"),
                "Device ID": device.get("Device ID")
            }

            if device.get("Subsystem ID"):
                controller_info["Subsystem ID"] = device.get("Subsystem ID")

            if device.get("PCI Path"):
                controller_info["PCI Path"] = device.get("PCI Path")

            if device.get("ACPI Path"):
                controller_info["ACPI Path"] = device.get("ACPI Path")

            usb_controller_info[self.utils.get_unique_key(device_name, usb_controller_info)] = controller_info

        return usb_controller_info
                
    def input(self):
        input_info = {}
        INPUT_DEVICE_PATH = "/sys/class/input"

        if not os.path.exists(INPUT_DEVICE_PATH):
            return input_info

        bus_type_map = {
            "0003": "USB",
            "0011": "PS/2",
            "0018": "I2C",
            "0019": "SMBus"
        }

        for device in os.listdir(INPUT_DEVICE_PATH):
            if not device.startswith("input"):
                continue

            device_dir = os.path.join(INPUT_DEVICE_PATH, device)
            if not os.path.isdir(device_dir):
                continue

            try:
                device_name_path = os.path.join(device_dir, 'name')
                device_name = self._read_sys_file(device_name_path)

                id_dir = os.path.join(device_dir, 'id')
                bus_type_code = self._read_sys_file(os.path.join(id_dir, 'bustype'))
                vendor_id = self._read_sys_file(os.path.join(id_dir, 'vendor'))
                product_id = self._read_sys_file(os.path.join(id_dir, 'product'))
                
                bus_type = bus_type_map.get(bus_type_code, "Unknown")
                
                device_info = {
                    "Bus Type": bus_type,
                    "Device ID": f"{vendor_id}-{product_id}".upper()
                }

                device_symlink = os.path.join(device_dir, 'device')
                if os.path.islink(device_symlink):
                    target_path = os.readlink(device_symlink)
                    acpi_id_match = re.search(r'(PNP[A-F0-9]{4})', target_path.upper())
                    if acpi_id_match:
                        device_info["Device"] = acpi_id_match.group(1)
                        device_info["Bus Type"] = "ACPI"
                
                if "Sleep Button" in device_name or "Power Button" in device_name or "Video Bus" in device_name:
                    continue
                    
                input_info[self.utils.get_unique_key(device_name, input_info)] = device_info

            except (FileNotFoundError, IndexError):
                continue

        return input_info
    
    def storage_controllers(self):
        storage_controller_info = {}

        for device in self.devices_by_class.get("Non-Volatile memory controller", []) + self.devices_by_class.get("SATA controller", []):
            device_name = device.get("Name", "Unknown")
            device_dir = os.path.join(PCI_DEVICES_PATH, device.get("Device Path"))

            device_info = {
                "Bus Type": device.get("Bus Type"),
                "Device ID": device.get("Device ID")
            }

            if device.get("Subsystem ID"):
                device_info["Subsystem ID"] = device.get("Subsystem ID")

            if device.get("PCI Path"):
                device_info["PCI Path"] = device.get("PCI Path")

            if device.get("ACPI Path"):
                device_info["ACPI Path"] = device.get("ACPI Path")

            model_paths = self.utils.find_matching_paths(device_dir, name_filter="model", type_filter="file")
            disk_drive_names = []

            for model_path, _ in model_paths:
                try:
                    disk_drive_names.append(self._read_sys_file(os.path.join(device_dir, model_path)))
                except:
                    pass

            if disk_drive_names:
                device_info["Disk Drives"] = disk_drive_names

            storage_controller_info[self.utils.get_unique_key(device_name, storage_controller_info)] = device_info

        return storage_controller_info

    def biometric(self):
        biometric_info = {}

        ###

        return biometric_info
        
    def bluetooth(self):
        bluetooth_info = {}
        
        BLUETOOTH_DEVICE_PATH = "/sys/class/bluetooth"

        if not os.path.exists(BLUETOOTH_DEVICE_PATH):
            return bluetooth_info

        for device in os.listdir(BLUETOOTH_DEVICE_PATH):
            uevent = self._read_sys_file(os.path.join(BLUETOOTH_DEVICE_PATH, device, "device", "uevent"))

            if not uevent:
                continue

            vendor_id = product_id = class_id = bus_type = None

            for line in uevent.splitlines():
                lower_line = line.lower()

                if "product" in lower_line:
                    vendor_id, product_id, class_id = line.split("=")[-1].split("/")

                    vendor_id = vendor_id.zfill(4)
                    product_id = product_id.zfill(4)
                    class_id = class_id.zfill(4)
                elif "modalias" in lower_line:
                    bus_type = line.split("=")[-1].split(":")[0].upper()
            
            if not all((vendor_id, product_id)):
                continue

            device_name, device_class = self.get_usb_device_name_and_class(vendor_id, product_id)

            device_info = {}

            if bus_type:
                device_info["Bus Type"] = bus_type

            device_info["Device ID"] = "{}-{}".format(vendor_id, product_id).upper()

            bluetooth_info[self.utils.get_unique_key(device_name, bluetooth_info)] = device_info

        return bluetooth_info
                 
    def sd_controller(self):
        sd_controller_info = {}

        MMC_DEVICE_PATH = "/sys/class/mmc_host"

        if not os.path.exists(MMC_DEVICE_PATH):
            return sd_controller_info
        
        for device in os.listdir(MMC_DEVICE_PATH):
            device_dir = os.path.join(MMC_DEVICE_PATH, device, "device", "firmware_node")

            if not os.path.exists(device_dir):
                continue

            physical_nodes = self.utils.find_matching_paths(device_dir, name_filter="physical_node", type_filter="dir")

            if not physical_nodes:
                continue

            vendor_id = device_id = subsystem_vendor_id = subsystem_device_id = device_slot_name = bus_type = None

            for physical_node, _ in physical_nodes:
                uevent = self._read_sys_file(os.path.join(device_dir, physical_node, "uevent"))

                for line in uevent.splitlines():
                    lower_line = line.lower()

                    if "pci_id" in lower_line:
                        vendor_id, device_id = line.split("=")[-1].split(":")

                        vendor_id = vendor_id.zfill(4)
                        device_id = device_id.zfill(4)
                    elif "pci_subsys_id" in lower_line:
                        subsystem_vendor_id, subsystem_device_id = line.split("=")[-1].split(":")

                        subsystem_vendor_id = subsystem_vendor_id.zfill(4)
                        subsystem_device_id = subsystem_device_id.zfill(4)
                    elif "pci_slot_name" in lower_line:
                        device_slot_name = line.split("=")[-1]
                    elif "modalias" in lower_line:
                        if bus_type not in ("PCI", "USB"):
                            bus_type = line.split("=")[-1].split(":")[0].upper()

            if not all((bus_type, vendor_id, device_id)):
                continue

            device_name, device_class = self.get_pci_device_name_and_class(device_slot_name)

            device_info = {
                "Bus Type": bus_type,
                "Device ID": "{}-{}".format(vendor_id, device_id).upper()
            }

            if all((subsystem_vendor_id, subsystem_device_id)):
                device_info["Subsystem ID"] = "{}{}".format(subsystem_device_id, subsystem_vendor_id).upper()

            device_info.update(self.get_device_location_paths(os.path.dirname(device_dir)))

            sd_controller_info[self.utils.get_unique_key(device_name, sd_controller_info)] = device_info

        return sd_controller_info
        
    def system_devices(self):
        system_device_info = {}

        PLATFORM_DEVICE_PATH = "/sys/bus/platform/devices"

        if not os.path.exists(PLATFORM_DEVICE_PATH):
            return system_device_info
        
        for device in os.listdir(PLATFORM_DEVICE_PATH):
            device_dir = os.path.join(PLATFORM_DEVICE_PATH, device)

            if not os.path.exists(device_dir):
                continue

            device_info = {}

            bus_type = device_description = hid = None

            for property_name in os.listdir(device_dir):
                device_property_path = os.path.join(device_dir, property_name)

                if "firmware_node" in property_name:
                    for firmware_node_property in os.listdir(device_property_path):
                        firmware_node_property_path = os.path.join(device_property_path, firmware_node_property)

                        if "description" == firmware_node_property:
                            device_description = self._read_sys_file(firmware_node_property_path)
                        elif "hid" == firmware_node_property:
                            hid = self._read_sys_file(firmware_node_property_path)
                elif "modalias" == property_name:
                    bus_type_str = self._read_sys_file(device_property_path)
                    bus_type = bus_type_str.split(":")[0].upper() if bus_type_str else None  

            if not bus_type:
                continue

            device_info["Bus Type"] = bus_type
            device_info["Device"] = hid or device.split(":")[0].split(".")[0]

            device_info.update(self.get_device_location_paths(device_dir))

            system_device_info[self.utils.get_unique_key(device_description or hid or device.split(":")[0].split(".")[0], system_device_info)] = device_info

        for device_class in self.devices_by_class:
            if device_class in ("USB controller", "VGA compatible controller", "3D controller", "Non-Volatile memory controller", "SATA controller"):
                continue

            for device in self.devices_by_class[device_class]:
                device_name = device.get("Name", "Unknown")
                device_info = {
                    "Bus Type": device.get("Bus Type"),
                    "Device ID": device.get("Device ID")
                }

                if device.get("Subsystem ID"):
                    device_info["Subsystem ID"] = device.get("Subsystem ID")

                if device.get("PCI Path"):
                    device_info["PCI Path"] = device.get("PCI Path")

                if device.get("ACPI Path"):
                    device_info["ACPI Path"] = device.get("ACPI Path")

                system_device_info[self.utils.get_unique_key(device_name, system_device_info)] = device_info

        return system_device_info

    def hardware_collector(self):
        self.utils.head("Hardware Information Collection")
        print("")
        print("Please wait while we gather your hardware details")
        print("")
        self.result = {}

        steps = [
            ('Gathering PCI devices', self.pci_devices, None),
            ('Gathering motherboard information', self.motherboard, "Motherboard"),
            ('Gathering BIOS information', self.bios, "BIOS"),
            ('Gathering CPU information', self.cpu, "CPU"),
            ('Gathering GPU information', self.gpu, "GPU"),
            ('Gathering monitor information', self.monitor, "Monitor"),
            ('Gathering network information', self.network, "Network"),
            ('Gathering sound information', self.sound, "Sound"), # Get audio endpoints each sound device
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