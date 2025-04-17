from Scripts import utils
import os
import re

class WindowsDeviceLocator:
    def __init__(self):
        pass
    
    def convert_pci_path(self, path):
        components = path.split("#")
        result = []
        
        for component in components:
            if component.startswith("PCIROOT"):
                match = re.match(r"PCIROOT\((\d+)\)", component)
                if match:
                    result.append("PciRoot(0x{:x})".format(int(match.group(1))))
            elif component.startswith("PCI"):
                match = re.match(r"PCI\((\w+)\)", component)
                if match:
                    values = match.group(1)
                    if len(values) == 4:
                        bus = int(values[:2], 16)
                        device = int(values[2:], 16)
                        result.append("Pci(0x{:x},0x{:x})".format(bus, device))
                    else:
                        result.append("Pci(0x{:x})".format(int(values, 16)))
                        
        return "/".join(result)
    
    def convert_acpi_path(self, path):
        components = path.split("#")
        result = []
        
        for component in components:
            match = re.match(r'ACPI\((\w+)\)', component)
            if match:
                if result:
                    result.append(match.group(1))
                else:
                    result.append("\\{}".format(match.group(1)[:-1]))
                
        return ".".join(result)
    
    def get_device_location_paths(self, device):
        device_location_paths = {}

        try:
            location_paths = (device.GetDeviceProperties(["DEVPKEY_Device_LocationPaths"])[0][0].Data)
        except:
            return {}

        acpi_path = pci_path = None

        for path in location_paths:
            if path.startswith("ACPI") and not "#PCI" in path:
                acpi_path = self.convert_acpi_path(path)
            elif path.startswith("PCI"):
                pci_path = self.convert_pci_path(path)
        
        if pci_path:
            device_location_paths["PCI Path"] = pci_path

        if acpi_path:
            device_location_paths["ACPI Path"] = acpi_path

        return device_location_paths
        
class LinuxDeviceLocator:
    def __init__(self):
        self.utils = utils.Utils()

    def get_device_location_paths(self, device_dir):
        device_location_paths = {}

        uevent = self.utils.read_file(os.path.join(device_dir, "uevent")) or "\n"
        device_slot_name = None

        for line in uevent.split("\n"):
            lower_line = line.lower()

            if "pci_slot_name" in lower_line:
                device_slot_name = line.split("=")[1]
                break

        pci_path = None

        if device_slot_name:
            device_path = os.path.join("/sys/bus/pci/devices", device_slot_name)

            if os.path.exists(device_path):
                pci_root = "PciRoot({})".format(hex(int(device_slot_name.split(":")[0], 16)))

                pci_components = []

                children = self.utils.find_matching_paths(device_path, type_filter="dir")
                for child, _ in children:
                    if child.startswith("0000:") and child != device_slot_name:
                        bus_device_func = child.split(":")[-1]
                        bus, device_func = bus_device_func.split(".")
                        pci_components.append("Pci(0x{},0x{})".format(bus, device_func))

                if pci_components:
                    pci_components.sort(reverse=True)
                    pci_path = pci_root + "/" + "/".join(pci_components)

        if pci_path:
            device_location_paths["PCI Path"] = pci_path

        acpi_path = self.utils.read_file(os.path.join(device_dir, "firmware_node", "path"))
        if acpi_path:
            device_location_paths["ACPI Path"] = acpi_path.strip()

        return device_location_paths