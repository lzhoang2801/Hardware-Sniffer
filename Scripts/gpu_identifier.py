class GPUIdentifier:
    def identify_intel_graphics(self, hardware_id):
        gpu_codename = None
        device_id = hardware_id[5:]
        device_type = "Integrated GPU"

        if device_id.startswith("01"):
            if device_id[-2] in ("5", "6"):
                gpu_codename = "Ivy Bridge"
            else:
                gpu_codename = "Sandy Bridge"
        elif device_id.startswith(("04", "0A", "0C", "0D")):
            gpu_codename = "Haswell"
        elif device_id.startswith(("0B", "16")):
            gpu_codename = "Broadwell"
        elif device_id.startswith(("09", "19")):
            gpu_codename = "Skylake"
        elif device_id.startswith(("0A", "1A", "5A")):
            gpu_codename = "Apollo Lake"
        elif device_id.startswith("31"):
            gpu_codename = "Gemini Lake"
        elif device_id.startswith(("59", "87C0")):
            gpu_codename = "Kaby Lake"
        elif device_id.startswith(("3E", "87", "9B")):
            gpu_codename = "Coffee Lake"
        elif device_id.startswith("8A"):
            gpu_codename = "Ice Lake"
        elif device_id.startswith("4E"):
            gpu_codename = "Jasper Lake"
        elif device_id.startswith("9A"):
            gpu_codename = "Tiger Lake"
        elif device_id.startswith("45"):
            gpu_codename = "Elkhart Lake"
        elif device_id.startswith("4E"):
            gpu_codename = "Jasper Lake"
        elif device_id.startswith("4C"):
            gpu_codename = "Rocket Lake"
        elif device_id.startswith(("462", "46A")):
            gpu_codename = "Alder Lake-P"
        elif device_id.startswith("46D"):
            gpu_codename = "Alder Lake-N"
        elif device_id.startswith(("468", "469")):
            gpu_codename = "Alder Lake-S"
        elif device_id.startswith("49"):
            gpu_codename = "DG1"
            device_type = "Discrete GPU"
        elif device_id.startswith("A78"):
            gpu_codename = "Raptor Lake-S"
        elif device_id.startswith("A7"):
            gpu_codename = "Raptor Lake-P"
        elif device_id.startswith("56"):
            gpu_codename = "Alchemist"
            device_type = "Discrete GPU"
        elif device_id.startswith("0B"):
            gpu_codename = "Ponte Vecchio"
            device_type = "Discrete GPU"
        elif device_id.startswith("7D"):
            gpu_codename = "Meteor Lake"

        return {
            "Manufacturer": "Intel",
            "Codename": gpu_codename or "Unknown",
            "Device ID": hardware_id,
            "Device Type": "Unknown" if not gpu_codename else device_type
        }

    def identify_amd_graphics(self, hardware_id):
        gpu_codename = None
        device_id = hardware_id[5:]
        device_type = "Discrete GPU"

        if device_id.startswith("15D8"):
            gpu_codename = "Picasso"
            device_type = "Integrated GPU"
        elif device_id.startswith("15DD"):
            gpu_codename = "Raven Ridge"
            device_type = "Integrated GPU"
        elif device_id.startswith("15E7"):
            gpu_codename = "Barcelo"
            device_type = "Integrated GPU"
        elif device_id.startswith("1636"):
            gpu_codename = "Renoir"
            device_type = "Integrated GPU"
        elif device_id.startswith("1638"):
            gpu_codename = "Cezanne"
            device_type = "Integrated GPU"
        elif device_id.startswith("164C"):
            gpu_codename = "Lucienne"
            device_type = "Integrated GPU"
        elif device_id.startswith("164E"):
            gpu_codename = "Raphael"
            device_type = "Integrated GPU"
        elif device_id.startswith("164D"):
            gpu_codename = "Rembrandt"
            device_type = "Integrated GPU"
        elif device_id.startswith(("164F", "19")):
            gpu_codename = "Phoenix"
            device_type = "Integrated GPU"
        elif device_id.startswith("94C"):
            gpu_codename = "RV610"
        elif device_id.startswith("958"):
            gpu_codename = "RV630"
        elif device_id.startswith("940"):
            gpu_codename = "R600"
        elif device_id.startswith("95C"):
            gpu_codename = "RV620"
        elif device_id.startswith("959"):
            gpu_codename = "RV635"
        elif device_id.startswith("950F"):
            gpu_codename = "R680"
        elif device_id.startswith(("950", "951")):
            gpu_codename = "RV670"
        elif device_id.startswith(("9555", "9557")):
            gpu_codename = "RV711"
        elif device_id.startswith(("954", "955")):
            gpu_codename = "RV710"
        elif device_id.startswith("959"):
            gpu_codename = "RV635"
        elif device_id.startswith(("948", "949")):
            gpu_codename = "RV730"        
        elif device_id.startswith(("9441", "9443")):
            gpu_codename = "R700"
        elif device_id.startswith(("944", "945", "946A")):
            gpu_codename = "RV770"
        elif device_id.startswith(("946")):
            gpu_codename = "RV790"
        elif device_id.startswith(("68C", "68D")):
            gpu_codename = "Redwood"
        elif device_id.startswith(("68A", "68B")):
            gpu_codename = "Juniper"
        elif device_id.startswith("6880"):
            gpu_codename = "Lexington"
        elif device_id.startswith(("689C", "689D")):
            gpu_codename = "Hemlock"
        elif device_id.startswith(("688", "689")):
            gpu_codename = "Cypress"
        elif device_id.startswith("6750"):
            gpu_codename = "Onega"
        elif device_id.startswith(("674", "675")):
            gpu_codename = "Turks"
        elif device_id.startswith("673"):
            gpu_codename = "Barts"
        elif device_id.startswith(("671C", "671D")):
            gpu_codename = "Antilles"
        elif device_id.startswith(("670", "671")):
            gpu_codename = "Cayman"
        elif device_id.startswith(("68E8", "68E9", "68F")):
            gpu_codename = "Cedar"
        elif device_id.startswith(("6828", "6829", "682B", "683")):
            gpu_codename = "Cape Verde"
        elif device_id.startswith("682"):
            gpu_codename = "Venus"
        elif device_id.startswith("679B"):
            gpu_codename = "Malta"
        elif device_id.startswith(("678", "679")):
            gpu_codename = "Tahiti"
        elif device_id.startswith("677"):
            gpu_codename = "Caicos"
        elif device_id.startswith("67B9"):
            gpu_codename = "Vesuvius"
        elif device_id.startswith(("67A", "67B")):
            gpu_codename = "Hawaii"
        elif device_id.startswith(("6640", "6641", "6647")):
            gpu_codename = "Saturn"
        elif device_id.startswith(("664", "665")):
            gpu_codename = "Bonaire"
        elif device_id.startswith(("6810", "6811")):
            gpu_codename = "Curacao"
        elif device_id.startswith(("680", "681")):
            gpu_codename = "Pitcairn"
        elif device_id.startswith(("6929", "692B", "692F", "693")):
            gpu_codename = "Tonga"
        elif device_id.startswith("67B0"):
            gpu_codename = "Grenada"
        elif device_id.startswith("6907"):
            gpu_codename = "Meso"
        elif device_id.startswith("690"):
            gpu_codename = "Topaz"
        elif device_id.startswith("730"):
            gpu_codename = "Fiji"
        elif device_id.startswith(("6608", "6609", "661", "6631")):
            gpu_codename = "Oland"
        elif device_id.startswith(("67C", "67D")):
            gpu_codename = "Ellesmere"
        elif device_id.startswith(("67E", "67F")):
            gpu_codename = "Baffin"
        elif device_id.startswith(("698", "699")):
            gpu_codename = "Lexa"
        elif device_id.startswith("6FDF"):
            gpu_codename = "Polaris 20"
        elif device_id.startswith("694"):
            gpu_codename = "Polaris 22"
        elif device_id.startswith(("686", "687")):
            gpu_codename = "Vega 10"
        elif device_id.startswith("69A"):
            gpu_codename = "Vega 12"
        elif device_id.startswith("66A"):
            gpu_codename = "Vega 20"
        elif device_id.startswith("731"):
            gpu_codename = "Navi 10"
        elif device_id.startswith("736"):
            gpu_codename = "Navi 12"
        elif device_id.startswith("734"):
            gpu_codename = "Navi 14"
        elif device_id.startswith(("73A", "73B")):
            gpu_codename = "Navi 21"
        elif device_id.startswith(("73C", "73D")):
            gpu_codename = "Navi 22"
        elif device_id.startswith(("73E", "73FF")):
            gpu_codename = "Navi 23"
        elif device_id.startswith(("742", "743")):
            gpu_codename = "Navi 24"        
        elif device_id.startswith(("744", "745")):
            gpu_codename = "Navi 31"
        elif device_id.startswith(("746", "747")):
            gpu_codename = "Navi 32"
        elif device_id.startswith(("748", "749", "73F0")):
            gpu_codename = "Navi 33"

        return {
            "Manufacturer": "AMD",
            "Codename": gpu_codename or "Unknown",
            "Device ID": hardware_id,
            "Device Type": "Unknown" if not gpu_codename else device_type
        }

    def identify_nvidia_graphics(self, hardware_id):
        gpu_codename = "Unknown"
        device_id = hardware_id[5:]

        if device_id.startswith(("0FC", "0FD", "0FE", "0FF", "100", "101", "102", "103", "11", "128", "129", "12A", "12B", "130")) and device_id != "1140":
            gpu_codename = "Kepler"
        elif device_id.startswith(("05E", "05F", "0A2", "0A3", "0A6", "0A7", "0C", "10C", "10D")):
            gpu_codename = "Tesla"
        elif device_id.startswith(("06C", "06D", "0DC", "0DD", "0DE", "0DF", "0E2", "0E3", "0F0", "104", "105", "107", "108", "109", "114", "120", "121", "124", "125")):
            gpu_codename = "Fermi"
        elif device_id.startswith(("13", "14", "16", "17")) and not device_id.startswith("172"):
            gpu_codename = "Maxwell"
        elif device_id.startswith(("15", "172", "1B", "1C", "1D0", "1D1", "1D3", "1D5")):
            gpu_codename = "Pascal"
        
        return {
            "Manufacturer": "NVIDIA",
            "Codename": gpu_codename,
            "Device ID": hardware_id,
            "Device Type": "Discrete GPU"
        }

    def classify_gpu(self, hardware_id):
        if hardware_id.startswith("8086"):
            return self.identify_intel_graphics(hardware_id)
        elif hardware_id.startswith("1002"):
            return self.identify_amd_graphics(hardware_id)
        elif hardware_id.startswith("10DE"):
            return self.identify_nvidia_graphics(hardware_id)
        else:
            return {
                "Manufacturer": "Unknown",
                "Codename": "Unknown",
                "Device ID": hardware_id,
                "Device Type": "Unknown"
            }