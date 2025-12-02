import os
import sys
import json
import plistlib
import shutil
import zipfile

class Utils:
    def __init__(self, script_name = "Hardware Sniffer", rich_format=True):
        self.rich_format = rich_format
        self.script_name = script_name
    
    def get_full_path(self, *path):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            
        return os.path.join(base_path, *path)

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

                if isinstance(data, bytes) and sys.platform.startswith("linux") and file_path.startswith(("/sys/", "/proc/")) and "edid" not in os.path.basename(file_path).lower():
                    try:
                        data = data.decode("utf-8")
                    except:
                        pass
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

    def request_input(self, prompt="Press Enter to continue..."):
        if sys.version_info[0] < 3:
            user_response = raw_input(prompt)
        else:
            user_response = input(prompt)
        
        if not isinstance(user_response, str):
            user_response = str(user_response)
        
        return user_response

    def progress_bar(self, title, steps, current_step_index, done=False):
        self.head(title)
        print("")
        if done:
            for step in steps:
                print("  [{}] {}".format("\033[92m✓\033[0m" if self.rich_format else "*", step))
        else:
            for i, step in enumerate(steps):
                if i < current_step_index:
                    print("  [{}] {}".format("\033[92m✓\033[0m" if self.rich_format else "*", step))
                elif i == current_step_index:
                    print("  [{}] {}".format("\033[1;93m>\033[0m" if self.rich_format else ">", step))
                else:
                    print("  [ ] {}".format(step))
        print("")

    def head(self, text = None, width = 68, resize=True):
        if text == None:
            text = self.script_name
        
        os.system('cls' if os.name=='nt' else 'clear')

        if self.rich_format:
            if resize:
                self.adjust_window_size()

            separator = "═" * (width - 2)
            title = " {} ".format(text)
            if len(title) > width - 2:
                title = title[:width-4] + "..."
            title = title.center(width - 2)
            print("╔{}╗\n║{}║\n╚{}╝".format(separator, title, separator))
        else:
            print(text)
    
    def adjust_window_size(self, content=""):
        lines = content.splitlines()
        rows = len(lines)
        cols = max(len(line) for line in lines) if lines else 0
        print('\033[8;{};{}t'.format(max(rows+6, 30), max(cols+2, 100)))

    def exit_program(self):
        self.head()
        width = 68
        print("")
        print("For more information, to report errors, or to contribute to the product:".center(width))
        print("")

        separator = "─" * (width - 4)
        print(f" ┌{separator}┐ ")
        
        contacts = {
            "Facebook": "https://www.facebook.com/macforce2601",
            "Telegram": "https://t.me/lzhoang2601",
            "GitHub": "https://github.com/lzhoang2801/Hardware-Sniffer"
        }
        
        for platform, link in contacts.items():
            line = f" * {platform}: {link}"
            print(f" │{line.ljust(width - 4)}│ ")

        print(f" └{separator}┘ ")
        print("")
        print("Thank you for using our program!".center(width))
        print("")
        self.request_input("Press Enter to exit.".center(width))
        sys.exit(0)