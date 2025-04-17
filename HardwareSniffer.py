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
import getpass

os_name = platform.system()

class HardwareSniffer:
    def __init__(self):
        self.github = github.Github()
        self.fetcher = resource_fetcher.ResourceFetcher()
        self.run = run.Run().run
        self.u = utils.Utils()
        self.temporary_dir = tempfile.mkdtemp()
        self.result_dir = os.path.join(os.getcwd(), "Results")
        self.report_path = os.path.join(self.result_dir, "Report.json")

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

        output = os.path.join(self.result_dir, "ACPI")
        self.u.create_folder(output, remove_content=True)

        self.u.head("Dumping ACPI Tables")
        print("")
        print("Dumping tables...")
        
        if os_name == "Windows":
            cwd = os.getcwd()
            os.chdir(output)
            out = self.run({
                "args": [acpidump_path, "-b"]
            })
            os.chdir(cwd)
            if out[2] != 0:
                print(" - {}".format(out[1]))
                return

            tables = self.u.find_matching_paths(output, extension_filter=".dat")
            if not tables:
                print(" - No tables found!")
                print("")
                return

            for table_path, _ in tables:
                try:
                    os.rename(os.path.join(output, table_path), os.path.join(output, table_path[:-4] + ".aml"))
                except Exception as e:
                    print(" - {} -> {} failed: {}".format(os.path.basename(table_path), os.path.basename(table_path)[:-4] + ".aml", e))
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
            
            for table_path, _ in tables:
                destination_path = os.path.join(output, table_path.upper() + ".aml")

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
        print("Dumped ACPI tables to \"{}\"".format(output))
        print("")

    def main(self):
        full_report = False

        if os_name == "Windows":
            from Scripts.platforms.windows import WindowsHardwareInfo
            hardware_info = WindowsHardwareInfo()
            hardware_info.hardware_collector()
        elif os_name == "Linux":
            from Scripts.platforms.linux import LinuxHardwareInfo
            hardware_info = LinuxHardwareInfo()
            hardware_info.hardware_collector()
        else:
            raise NotImplementedError(f"Unsupported operating system: {os_name}")
        
        self.u.create_folder(self.result_dir)

        def generate_tree_content(data, prefix='', indent=0):
            content = ""
            if not data:
                return prefix + '└── (empty)\n'
            
            keys = list(data.keys())
            pointers = ['├── '] * (len(keys) - (2 if not full_report and not indent else 1)) + ['└── ']

            for pointer, key in zip(pointers, keys):
                value = data[key]
                content += prefix + pointer + key
                
                if isinstance(value, dict):
                    if not full_report and indent > 0:
                        content += "\n"
                        continue
                    extension = '│   ' if pointer == '├── ' else '    '
                    content += "\n" + generate_tree_content(value, prefix + extension, indent + 1)
                else:
                    content += ': ' + str(value) + "\n"

            return content

        while True:
            current_mode = "Full" if full_report else "Short"
            next_mode = "Short" if full_report else "Full"
            contents = []
            contents.append("")
            contents.append("Your hardware details:")
            contents.append(generate_tree_content(hardware_info.result))
            contents.append("T. Toggle hardware report view: \033[1;36m{}\033[0m / {}".format(current_mode, next_mode))
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
            elif option.lower() == "t":
                full_report = not full_report
            elif option.lower() == "h":
                self.u.write_file(self.report_path, hardware_info.result)
                print("")
                print("Report saved to \"{}\"".format(self.report_path))
                print("")
                self.u.request_input()
            elif option.lower() == "a":
                self.dump_acpi_tables()
                self.u.request_input()

if __name__ == '__main__':
    h = HardwareSniffer()
    while True:
        try:
            h.main()
        except Exception as e:
            h.u.head("An Error Occurred")
            print("")
            print(traceback.format_exc())
            h.u.request_input()
