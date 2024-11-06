# -*- coding: utf-8 -*-

from Scripts import github
from Scripts import resource_fetcher
from Scripts import run
from Scripts import utils
import os
import platform
import tempfile
import shutil
import argparse
import sys

os_name = platform.system()

class HardwareSniffer:
    def __init__(self, results_dir):
        self.github = github.Github()
        self.fetcher = resource_fetcher.ResourceFetcher()
        self.run = run.Run().run
        self.u = utils.Utils()
        self.temporary_dir = tempfile.mkdtemp()
        self.results_dir = results_dir
        self.report_path = os.path.join(self.results_dir, "Report.json")

    def get_latest_acpidump(self):
        latest_release = self.github.get_latest_release("acpica", "acpica") or {}
        
        for asset in latest_release.get("assets"):
            if asset.get("product_name") == "acpidump":
                return asset.get("url")
            
        return None

    def check_acpidump(self):
        acpidump_path = os.path.join(os.getcwd(), "acpidump.exe")

        if os.path.exists(acpidump_path):
            return acpidump_path
        
        print("Gathering Files")
        print("")
        print("Please wait for download acpidump...")
        print("")
        
        acpidump_download_link = self.get_latest_acpidump()
        if not acpidump_download_link: 
            raise Exception("Could not get latest acpidump")
        
        try:
            self.fetcher.download_and_save_file(acpidump_download_link, acpidump_path)
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

        output = os.path.join(self.results_dir, "ACPITables")
        self.u.create_folder(output)

        print("")
        print("")
        print("Dumping ACPI Tables")
        print("")
        
        if os_name == "Windows":
            print("Dumping tables to {}...".format(output))

            cwd = os.getcwd()
            os.chdir(output)
            out = self.run({
                "args":[acpidump_path, "-b"]
            })
            os.chdir(cwd)
            if out[2] != 0:
                print(" - {}".format(out[1]))
                return
            print("Updating names...")

            table_paths = self.u.find_matching_paths(output, extension_filter=".dat")
            for path, type in table_paths:
                try:
                    os.rename(os.path.join(output, path), os.path.join(output, path[:-4] + ".aml"))
                except Exception as e:
                    print(" - {} -> {} failed: {}".format(os.path.basename(path), os.path.basename(path)[:-4] + ".aml", e))
                
        print("")
        print("Dump successful!")
        print("")

    def main(self):
        self.u.create_folder(self.results_dir, remove_content=True)

        print("Hardware Information Collection")
        print("")
        print("Please wait while we gather your hardware details")
        print("")

        report_data = {}

        if os_name == "Windows":
            from Scripts.platforms.windows import WindowsHardwareInfo
            hardware_info = WindowsHardwareInfo()       
        else:
            raise NotImplementedError(f"Unsupported operating system: {os_name}")
        
        steps = [
            ('Gathering PnP devices', hardware_info.pnp_devices, None),
            ('Gathering motherboard information', hardware_info.motherboard, "Motherboard"),
            ('Gathering CPU information', hardware_info.cpu, "CPU"),
            ('Gathering GPU information', hardware_info.gpu, "GPU"),
            ('Gathering monitor information', hardware_info.monitor, "Monitor"),
            ('Gathering network information', hardware_info.network, "Network"),
            ('Gathering sound information', hardware_info.sound, "Sound"),
            ('Gathering USB controllers', hardware_info.usb_controllers, "USB Controllers"),
            ('Gathering input devices', hardware_info.input, "Input"),
            ('Gathering storage controllers', hardware_info.storage_controllers, "Storage Controllers"),
            ('Gathering biometric information', hardware_info.biometric, "Biometric"),
            ('Gathering bluetooth information', hardware_info.bluetooth, "Bluetooth"),
            ('Gathering sd controller information', hardware_info.sd_controller, "SD Controller"),
            ('Gathering system devices', hardware_info.system_devices, "System Devices")
        ]

        total_steps = len(steps)
        for index, (message, function, attribute) in enumerate(steps, start=1):
            print(f"[{index}/{total_steps}] {message}...")
            value = function()
            if not attribute:
                continue
            if value:
                report_data[attribute] = value
            else:
                print("    - No {} found.".format(attribute.lower()))

        print("")
        print("Hardware information collection complete.")

        self.u.write_file(self.report_path, report_data)
        print("")
        print("Report saved to \"{}\"".format(self.report_path))
        print("")
        self.dump_acpi_tables()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--export", action="store_true", help="Export hardware report and ACPI tables")
    parser.add_argument("-o", "--output-dir", default="SysReport", help="Specify a custom output directory to save the exported files, default to SysReport")
    args = parser.parse_args()

    h = HardwareSniffer(args.output_dir)

    if not args.export:
        parser.print_help()
        sys.exit(1)

    h.main()