# -*- coding: utf-8 -*-

from Scripts import github
from Scripts import resource_fetcher
from Scripts import run
from Scripts import utils
import os
import platform
import tempfile
import shutil
import traceback
import sys
import getpass

os_name = platform.system()

class HardwareSniffer:
    def __init__(self, result_dir="SysReport", rich_format=True):
        self.github = github.Github()
        self.fetcher = resource_fetcher.ResourceFetcher()
        self.run = run.Run().run
        self.u = utils.Utils(rich_format=rich_format)
        self.temporary_dir = tempfile.mkdtemp()
        self.result_dir = result_dir

        if os_name == "Windows":
            from Scripts.platforms.windows import WindowsHardwareInfo
            self.hardware_info = WindowsHardwareInfo(rich_format=rich_format)
        elif os_name == "Linux":
            from Scripts.platforms.linux import LinuxHardwareInfo
            self.hardware_info = LinuxHardwareInfo(rich_format=rich_format)
        else:
            raise NotImplementedError(f"Unsupported operating system: {os_name}")

    def generate_summary_view(self):
        data = self.hardware_info.result.copy()
        summary = [""]
        
        if "Motherboard" in data and data["Motherboard"]:
            mobo_name = data["Motherboard"].get("Name", "N/A")
            chipset = data["Motherboard"].get("Chipset", "N/A")
            summary.append("Motherboard: {} ({})".format(mobo_name, chipset))

        if "BIOS" in data and data["BIOS"]:
            bios_version = data["BIOS"].get("Version", "N/A")
            bios_release_date = data["BIOS"].get("Release Date", "N/A")
            system_type = data["BIOS"].get("System Type", "N/A")
            firmware_type = data["BIOS"].get("Firmware Type", "N/A")
            secure_boot = data["BIOS"].get("Secure Boot", "N/A")
            summary.append("BIOS: {} ({}), {}, {}, {} Secure Boot".format(bios_version, bios_release_date, system_type, firmware_type, secure_boot.lower()))
        
        if "CPU" in data and data["CPU"]:
            cpu_name = data["CPU"].get("Processor Name", "N/A")
            cpu_name = cpu_name[:36] + "..." if len(cpu_name) > 36 else cpu_name
            codename = data["CPU"].get("Codename", "N/A")
            summary.append("CPU: {} ({})".format(cpu_name, codename))

        if "GPU" in data and data["GPU"]:
            for index, (gpu_name, gpu_data) in enumerate(data["GPU"].items(), start=1):
                codename = gpu_data.get("Codename", "N/A")
                gpu_name = gpu_name[:36] + "..." if len(gpu_name) > 36 else gpu_name
                summary.append("GPU {}: {} ({})".format(index, gpu_name, codename))
                if "Monitor" in data and data["Monitor"]:
                    monitors = {monitor_name: monitor_data for monitor_name, monitor_data in data["Monitor"].items() if monitor_data.get("Connected GPU") == gpu_name}
                    if monitors:
                        summary.append("   Monitors: {}".format(", ".join(
                            [
                                "{} ({}, {})".format(monitor_name, monitor_data.get("Connector Type", "N/A"), monitor_data.get("Resolution", "N/A"))
                                for monitor_name, monitor_data in monitors.items()
                            ]
                        )))

        if "Network" in data and data["Network"]:
            for index, (network_name, network_data) in enumerate(data["Network"].items(), start=1):
                bus_type = network_data.get("Bus Type", "N/A")
                device_id = network_data.get("Device ID", "N/A")
                network_name = network_name[:36] + "..." if len(network_name) > 36 else network_name
                summary.append("Network {}: {} ({}, {})".format(index, network_name, bus_type, device_id))

        if "Sound" in data and data["Sound"]:
            for index, (sound_name, sound_data) in enumerate(data["Sound"].items(), start=1):
                bus_type = sound_data.get("Bus Type", "N/A")
                device_id = sound_data.get("Device ID", "N/A")
                audio_endpoints = sound_data.get("Audio Endpoints", [])
                summary.append("Sound {}: {} ({}, {})".format(index, sound_name, bus_type, device_id))
                if audio_endpoints:
                    summary.append("   Audio Endpoints: {}".format(", ".join(audio_endpoints)))

        if "USB Controllers" in data and data["USB Controllers"]:
            for index, (usb_controller_name, usb_controller_data) in enumerate(data["USB Controllers"].items(), start=1):
                bus_type = usb_controller_data.get("Bus Type", "N/A")
                device_id = usb_controller_data.get("Device ID", "N/A")
                usb_controller_name = usb_controller_name[:36] + "..." if len(usb_controller_name) > 36 else usb_controller_name
                summary.append("USB Controller {}: {} ({}, {})".format(index, usb_controller_name, bus_type, device_id))

        if "Input" in data and data["Input"]:
            for index, (input_name, input_data) in enumerate(data["Input"].items(), start=1):
                bus_type = input_data.get("Bus Type", "N/A")
                device_id = input_data.get("Device ID", "N/A")
                input_name = input_name[:36] + "..." if len(input_name) > 36 else input_name
                summary.append("Input {}: {} ({}, {})".format(index, input_name, bus_type, device_id))

        if "Storage Controllers" in data and data["Storage Controllers"]:
            for index, (storage_controller_name, storage_controller_data) in enumerate(data["Storage Controllers"].items(), start=1):
                bus_type = storage_controller_data.get("Bus Type", "N/A")
                device_id = storage_controller_data.get("Device ID", "N/A")
                disk_drives = storage_controller_data.get("Disk Drives", [])
                storage_controller_name = storage_controller_name[:36] + "..." if len(storage_controller_name) > 36 else storage_controller_name
                summary.append("Storage Controller {}: {} ({}, {})".format(index, storage_controller_name, bus_type, device_id))
                if disk_drives:
                    summary.append("   Disk Drives: {}".format(", ".join(disk_drives)))

        if "Biometric" in data and data["Biometric"]:
            for index, (biometric_name, biometric_data) in enumerate(data["Biometric"].items(), start=1):
                device_id = biometric_data.get("Device ID", "N/A")
                biometric_name = biometric_name[:36] + "..." if len(biometric_name) > 36 else biometric_name
                summary.append("Biometric {}: {} ({})".format(index, biometric_name, device_id))

        if "Bluetooth" in data and data["Bluetooth"]:
            for index, (bluetooth_name, bluetooth_data) in enumerate(data["Bluetooth"].items(), start=1):
                bus_type = bluetooth_data.get("Bus Type", "N/A")
                device_id = bluetooth_data.get("Device ID", "N/A")
                bluetooth_name = bluetooth_name[:36] + "..." if len(bluetooth_name) > 36 else bluetooth_name
                summary.append("Bluetooth {}: {} ({}, {})".format(index, bluetooth_name, bus_type, device_id))

        if "SD Controller" in data and data["SD Controller"]:
            for index, (sd_controller_name, sd_controller_data) in enumerate(data["SD Controller"].items(), start=1):
                bus_type = sd_controller_data.get("Bus Type", "N/A")
                device_id = sd_controller_data.get("Device ID", "N/A")
                sd_controller_name = sd_controller_name[:36] + "..." if len(sd_controller_name) > 36 else sd_controller_name
                summary.append("SD Controller {}: {} ({}, {})".format(index, sd_controller_name, bus_type, device_id))

        return "\n".join(summary)

    def export_hardware_report(self):
        self.u.head("Exporting Hardware Report")
        print("")

        try:
            self.u.create_folder(self.result_dir)
            
            self.report_path = os.path.join(self.result_dir, "Report.json")

            self.u.write_file(self.report_path, self.hardware_info.result)
            print("Report saved to `{}`".format(self.report_path))
        except Exception as e:
            print(f"Error exporting report: {e}", file=sys.stderr)
            traceback.print_exc()

        print("")

    def get_latest_acpidump(self):
        return "https://github.com/acpica/acpica/releases/download/R2024_12_12/acpidump.exe"

        latest_release = self.github.get_latest_release("acpica", "acpica") or {}
        
        for asset in latest_release.get("assets"):
            if asset.get("product_name") == "acpidump":
                return asset.get("url")
            
        return None

    def check_acpidump(self):
        acpidump_path = os.path.join(os.getcwd(), "acpidump.exe")

        if os.path.exists(acpidump_path):
            return acpidump_path
        
        self.u.head("Gathering Files")
        print("")
        print("Please wait for download acpidump...")
        
        acpidump_download_link = self.get_latest_acpidump()
        if not acpidump_download_link: 
            raise Exception("Could not find download URL for acpidump.exe.")
        
        try:
            self.fetcher.download_and_save_file(acpidump_download_link, acpidump_path)

            if not os.path.exists(acpidump_path):
                raise Exception("Failed to download acpidump.exe.")
        except:
            raise Exception("Could not locate or download acpidump.exe!\n\nPlease manually download acpidump.exe from:\n - {}\n\nAnd place in:\n - {}\n".format(
                "https://github.com/acpica/acpica/releases",
                os.path.dirname(os.path.realpath(__file__))
            ))
            
        shutil.rmtree(self.temporary_dir, ignore_errors=True)
        
        return acpidump_path

    def dump_acpi_tables(self):
        if os_name == "Windows":
            acpidump_path = self.check_acpidump()

        acpi_dir = os.path.join(self.result_dir, "ACPI")
        self.u.create_folder(acpi_dir, remove_content=True)

        self.u.head("Dumping ACPI Tables")
        print("")
        print("Dumping tables to {}...".format(acpi_dir))
        
        if os_name == "Windows":
            cwd = os.getcwd()
            os.chdir(acpi_dir)
            out = self.run({
                "args":[acpidump_path, "-b"]
            })
            os.chdir(cwd)
            if out[2] != 0:
                print(" - {}".format(out[1]))
                return
            print("Updating names...")

            table_paths = self.u.find_matching_paths(acpi_dir, extension_filter=".dat")
            for path, type in table_paths:
                try:
                    os.rename(os.path.join(acpi_dir, path), os.path.join(acpi_dir, path[:-4] + ".aml"))
                except Exception as e:
                    print(" - {} -> {} failed: {}".format(os.path.basename(path), os.path.basename(path)[:-4] + ".aml", e))
        elif os_name == "Linux":
            table_dir = "/sys/firmware/acpi/tables"
            if not os.path.isdir(table_dir):
                print("Could not locate {}!".format(table_dir))
                return
            
            tables = self.u.find_matching_paths(table_dir, type_filter="file")
            if not tables:
                print(" - No tables found!")
                print("")
                return
            
            for table_path, type in tables:
                destination_path = os.path.join(acpi_dir, table_path.upper() + ".aml")
                self.u.create_folder(os.path.dirname(destination_path))

                out = self.run({
                    "args": ["sudo", "cp", os.path.join(table_dir, table_path), destination_path]
                })
                if out[2] != 0:
                    print(" - {}".format(out[1]))
                    return
                
                out = self.run({
                    "args": ["sudo", "chown", getpass.getuser(), destination_path]
                })
                if out[2] != 0:
                    print(" - {}".format(out[1]))
                    return

        print("")
        print("ACPI tables dumped successfully.")
        print("")

    def main(self):
        self.hardware_info.hardware_collector()

        while True:
            contents = []
            contents.append("")
            contents.append("Your hardware details:")
            contents.append(self.generate_summary_view())
            contents.append("")
            contents.append("H. Export hardware report")
            contents.append("A. Dump ACPI Tables")
            contents.append("")
            contents.append("Q. Quit")
            contents.append("")
            content = "\n".join(contents)

            self.u.adjust_window_size(content)
            self.u.head("Hardware Sniffer", resize=False)
            print(content)
            option = self.u.request_input("Please make a selection: ")
            if option.lower() == "q":
                self.u.exit_program()
            elif option.lower() == "h":
                self.export_hardware_report()
                self.u.request_input()
            elif option.lower() == "a":
                self.dump_acpi_tables()
                self.u.request_input()

if __name__ == '__main__':
    HardwareSniffer().main()