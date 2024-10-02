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