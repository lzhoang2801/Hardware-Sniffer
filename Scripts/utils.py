import os
import json
import plistlib
import shutil
import subprocess
import zipfile

class Utils:
    def __init__(self, script_name = "Hardware Sniffer"):
        self.script_name = script_name
        self.pci_ids = self.read_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "datasets", "usb.ids"))
        self.usb_ids = self.read_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "datasets", "usb.ids"))
    
    def write_file(self, file_path, data):
        file_extension = os.path.splitext(file_path)[1]

        with open(file_path, "w" if file_extension == ".json" else "wb") as file:
            if file_extension == ".json":
                json.dump(data, file, indent=4)
            else:
                if file_extension == ".plist":
                    data = plistlib.dumps(data)

                file.write(data)

    def read_file(self, file_path):
        if not os.path.exists(file_path):
            return None

        file_extension = os.path.splitext(file_path)[1]

        with open(file_path, "r" if file_extension == ".json" else "rb") as file_handle:
            if file_extension == ".plist":
                data = plistlib.load(file_handle)
            elif file_extension == ".json":
                data = json.load(file_handle)
            elif file_extension == ".ids":
                data = {}
                current_vendor = None
                
                for line in file_handle.read().decode().splitlines():
                    if not line.strip() or line.startswith("#"):
                        continue
                    
                    if not line.startswith("\t"):
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2:
                            current_vendor = parts[0].upper()
                            data[current_vendor] = {"name": parts[1], "devices": {}}
                    
                    elif current_vendor:
                        parts = line.strip().split(maxsplit=1)
                        if len(parts) == 2:
                            device_id, device_name = parts
                            data[current_vendor]["devices"][device_id.upper()] = device_name
            else:
                data = file_handle.read()
        return data

    def find_matching_paths(self, root_path, extension_filter=None, name_filter=None, type_filter=None):

        def is_valid_item(name):
            if name.startswith("."):
                return False
            if extension_filter and not name.lower().endswith(extension_filter.lower()):
                return False
            if name_filter and name_filter not in name:
                return False
            return True
        
        found_paths = []

        for root, dirs, files in os.walk(root_path):
            relative_root = root.replace(root_path, "")[1:]

            if type_filter in (None, "dir"):
                for d in dirs:
                    if is_valid_item(d):
                        found_paths.append((os.path.join(relative_root, d), "dir"))

            if type_filter in (None, "file"):
                for file in files:
                    if is_valid_item(file):
                        found_paths.append((os.path.join(relative_root, file), "file"))

        return sorted(found_paths, key=lambda path: path[0])
 
    def create_folder(self, path, remove_content=False):
        if os.path.exists(path):
            if remove_content:
                shutil.rmtree(path)
                os.makedirs(path)
        else:
            os.makedirs(path)
    
    def get_unique_key(self, base_key, dictionary):
        if base_key not in dictionary:
            return base_key
        
        counter = 1
        unique_key = f"{base_key}_#{counter}"
        
        while unique_key in dictionary:
            counter += 1
            unique_key = f"{base_key}_#{counter}"
        
        return unique_key
        
    def extract_zip_file(self, zip_path, extraction_directory=None):
        if extraction_directory is None:
            extraction_directory = os.path.splitext(zip_path)[0]
        
        os.makedirs(extraction_directory, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_directory)

    def contains_any(self, data, search_item, start=0, end=None):
        return next((item for item in data[start:end] if item.lower() in search_item.lower()), None)

    def open_folder(self, folder_path):
        if os.name == 'posix':
            if 'darwin' in os.uname().sysname.lower():
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        elif os.name == 'nt':
            os.startfile(folder_path)
        else:
            raise NotImplementedError("This function is only supported on macOS, Windows, and Linux.")

    def request_input(self, prompt="Press Enter to continue..."):
        try:
            user_response = input(prompt)
        except NameError:
            user_response = raw_input(prompt)
        
        if not isinstance(user_response, str):
            user_response = str(user_response)
        
        return user_response

    def clear_screen(self):
    	os.system('cls' if os.name=='nt' else 'clear')

    def head(self, text = None, width = 68, resize=True):
        if resize:
            self.adjust_window_size()
        self.clear_screen()
        if text == None:
            text = self.script_name
        separator = "#" * width
        title = " {} ".format(text)
        if len(title) > width - 2:
            title = title[:width-4] + "..."
        title = title.center(width - 2)  # Center the title within the width minus 2 for the '#' characters
        
        print("{}\n#{}#\n{}".format(separator, title, separator))
    
    def adjust_window_size(self, content=""):
        lines = content.splitlines()
        rows = len(lines)
        cols = max(len(line) for line in lines) if lines else 0
        print('\033[8;{};{}t'.format(max(rows+10, 24), max(cols+2, 80)))

    @staticmethod
    def message(text, msg_type="attention"):
        # ANSI escape codes for different colors and bold font
        RED_BOLD = "\033[1;31m"
        YELLOW_BOLD = "\033[1;33m"
        CYAN_BOLD = "\033[1;36m"
        RESET = "\033[0m"
        
        if msg_type == "attention":
            color_code = RED_BOLD
        elif msg_type == "warning":
            color_code = YELLOW_BOLD
        elif msg_type == "reminder":
            color_code = CYAN_BOLD
        else:
            color_code = RESET

        return "{}{}{}".format(color_code, text, RESET)

    def exit_program(self, custom_content=""):
        self.head()
        print(custom_content)
        print("For more information, to report errors, or to contribute to the product:")
        print("* Facebook: https://www.facebook.com/macforce2601")
        print("* Telegram: https://t.me/lzhoang2601")
        print("* GitHub: https://github.com/lzhoang2801/OpCore-Simplify")
        print("")

        print("Thank you for using our program!\n")
        exit(0)