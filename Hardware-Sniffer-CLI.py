import argparse
import HardwareSniffer
import platform
import sys
import os

os_name = platform.system()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--export", action="store_true", help="export system report")
    parser.add_argument("-o", "--output-dir", default="SysReport", help="custom output directory to save system report, default to SysReport")
    args = parser.parse_args()

    h = HardwareSniffer.HardwareSniffer()

    h.result_dir = args.output_dir

    if os_name != "Windows":
        raise NotImplementedError(f"Unsupported operating system: {os_name}")

    if not args.export:
        parser.print_help()
        sys.exit(1)

    from Scripts.platforms.windows import WindowsHardwareInfo
    hardware_info = WindowsHardwareInfo()
    hardware_info.hardware_collector()

    h.u.create_folder(h.result_dir)

    h.u.write_file(os.path.join(h.result_dir, "Report.json"), hardware_info.result)
    print("")
    print("Report saved to \"{}\"".format(h.report_path))
    print("")

    h.dump_acpi_tables()

    print("Done.")

    sys.exit(0)