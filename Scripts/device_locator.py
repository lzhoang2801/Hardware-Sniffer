from Scripts import run
import re

class WindowsDeviceLocator:
    def __init__(self):
        self.run = run.Run().run
    
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
        if "PCI(" in path:
            return ""
        
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
    
    def get_device_location_paths(self, pnp_device_id):
        get_location_paths_command = (
            'Get-PnpDeviceProperty -InstanceId "{}" '
            '-KeyName DEVPKEY_Device_LocationPaths | Select-Object -ExpandProperty Data'
        )
        
        output = self.run({
            "args":["powershell", "-Command", get_location_paths_command.format(pnp_device_id)]
        })
        
        if output[-1] != 0 or not output[0]:
            return None
        
        location_paths = output[0].strip().splitlines()
        pci_path = self.convert_pci_path(location_paths[0])
        acpi_path = self.convert_acpi_path(location_paths[-1])
        
        if not pci_path and not acpi_path:
            return None
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