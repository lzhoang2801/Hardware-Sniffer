# -*- coding: utf-8 -*-

from Scripts import resource_fetcher
from Scripts import run
from Scripts import utils
import os
import platform
import tempfile
import shutil
import traceback

os_name = platform.system()

class HardwareSniffer:
    def __init__(self):
        self.fetcher = resource_fetcher.ResourceFetcher()
        self.run = run.Run().run
        self.u = utils.Utils()
        self.temporary_dir = tempfile.mkdtemp()
        self.acpi_binary_tools = "https://www.intel.com/content/www/us/en/developer/topic-technology/open/acpica/download.html"
        self.result_dir = os.path.join(os.getcwd(), "Results")
        self.report_path = os.path.join(self.result_dir, "Report.json")

    def get_latest_acpi_binary_tools(self):
        # Source: https://github.com/corpnewt/SSDTTime/blob/64446d553fcbc14a4e6ebf3d8d16e3357b5cbf50/Scripts/dsdt.py#L243C5-L273C20
        
        # Helper to scrape https://www.intel.com/content/www/us/en/developer/topic-technology/open/acpica/download.html for the latest
        # download binaries link - then scrape the contents of that page for the actual download as needed
        try:
            source = self.fetcher.fetch_and_parse_content(self.acpi_binary_tools)
            for line in source.split("\n"):
                if '<a href="' in line and ">iasl compiler and windows acpi tools" in line.lower():
                    # Check if we have a direct download link - i.e. ends with .zip - or if we're
                    # redirected to a different download page - i.e. ends with .html
                    dl_link = line.split('<a href="')[1].split('"')[0]
                    if dl_link.lower().endswith(".zip"):
                        # Direct download - return as-is
                        return dl_link
                    elif dl_link.lower().endswith((".html",".htm")):
                        # Redirect - try to scrape for a download link
                        try:
                            if dl_link.lower().startswith(("http:","https:")):
                                # The existing link is likely complete - use it as-is
                                dl_page_url = dl_link
                            else:
                                # <a href="/content/www/us/en/download/774881/acpi-component-architecture-downloads-windows-binary-tools.html">iASL Compiler and Windows ACPI Tools
                                # Only a suffix - prepend to it
                                dl_page_url = "https://www.intel.com" + line.split('<a href="')[1].split('"')[0]
                            dl_page_source = self.dl.get_string(dl_page_url, progress=False, headers=self.h)
                            for line in dl_page_source.split("\n"):
                                if 'data-href="' in line and '"download-button"' in line:
                                    # Should have the right line
                                    return line.split('data-href="')[1].split('"')[0]
                        except: pass
        except: pass
        return None

    def check_acpidump(self):
        acpidump_path = self.u.get_full_path("Scripts", "acpidump.exe")

        if os.path.exists(acpidump_path):
            return acpidump_path
        
        self.u.head("Gathering Files")
        print("")
        print("Please wait for download ACPI Binary Tools...")
        print("")
        
        acpi_binary_tools_url = self.get_latest_acpi_binary_tools()
        if not acpi_binary_tools_url: 
            raise Exception("Could not get latest ACPI Binary Tools for Windows")
        
        self.u.create_folder(self.temporary_dir)
        zip_path = os.path.join(self.temporary_dir, os.path.basename(acpi_binary_tools_url))
        self.fetcher.download_and_save_file(acpi_binary_tools_url, zip_path)
        self.u.extract_zip_file(zip_path)
        
        try:
            source_acpidump_path = os.path.join(self.temporary_dir, self.u.find_matching_paths(self.temporary_dir, name_filter="acpidump")[0][0])
            shutil.move(source_acpidump_path, acpidump_path)
        except:
            raise Exception("Could not locate or download acpidump.exe!\n\nPlease manually download acpidump.exe from:\n - {}\n\nAnd place in:\n - {}\n".format(
                self.acpi_binary_tools,
                os.path.dirname(os.path.realpath(__file__))
            ))
            
        shutil.rmtree(self.temporary_dir, ignore_errors=True)
        
        return acpidump_path

    def dump_acpi_tables(self):
        if os_name == "Windows":
            acpidump_path = self.check_acpidump()

        output = os.path.join(self.result_dir, "ACPITables")
        self.u.create_folder(output, remove_content=True)

        self.u.head("Dumping ACPI Tables")
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
        self.u.request_input()

    def main(self):
        full_report = False

        if os_name == "Windows":
            from Scripts.platforms.windows import WindowsHardwareInfo
            hardware_info = WindowsHardwareInfo()
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
                self.u.write_file(os.path.join(self.result_dir, "Report.json"), hardware_info.result)
                print("")
                print("Report saved to \"{}\"".format(self.report_path))
                print("")
                self.u.open_folder(self.result_dir)
                self.u.request_input()
            elif option.lower() == "a":
                self.dump_acpi_tables()

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
