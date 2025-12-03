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
        
        if not pci_path and not acpi_path:
            return {}
        elif not pci_path:
            return {
                "ACPI Path": acpi_path
            }
        elif not acpi_path:
            return {
                "PCI Path": pci_path
            }
        else:
            return {
                "PCI Path": pci_path,
                "ACPI Path": acpi_path
            }
        
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
                real_path = os.path.realpath(device_path)
                
                pci_segments = []
                path_parts = real_path.split("/")
                
                domain = None
                for part in path_parts:
                    if part.startswith("pci") and ":" in part:
                        domain = int(part[3:].split(":")[0], 16)
                    elif ":" in part and "." in part:
                        segments = part.replace(":", ".").split(".")
                        if len(segments) >= 4:
                            device = int(segments[2], 16)
                            function = int(segments[3], 16)
                            pci_segments.append("Pci(0x{:x},0x{:x})".format(device, function))
                
                if domain is not None and pci_segments:
                    pci_path = "PciRoot(0x{:x})/{}".format(domain, "/".join(pci_segments))

        if pci_path:
            device_location_paths["PCI Path"] = pci_path

        acpi_path = self.utils.read_file(os.path.join(device_dir, "firmware_node", "path"))
        if acpi_path:
            acpi_path = acpi_path.strip()
            if acpi_path.startswith("\\_SB_."):
                acpi_path = "\\_SB." + acpi_path[6:]
            device_location_paths["ACPI Path"] = acpi_path

        return device_location_paths