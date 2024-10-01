from Scripts.datasets import cpu_data

class CPUIdentifier:
    def lookup_codename(self, processor_name, cpu_identifier):
        if cpu_identifier in "Family 6 Model 142 Stepping 10":
            if ("0U" in processor_name or "7U" in processor_name) and "82" not in processor_name:
                return "Kaby Lake-R"
        
        for entry in cpu_data.identifier[::-1]:
            codename, identifier = entry[:2]
            name_hint = entry[-1] if len(entry) > 2 else None
            if identifier in cpu_identifier:
                if name_hint:
                    if name_hint in processor_name:
                        return codename
                else:
                    return codename

        return "Unknown"