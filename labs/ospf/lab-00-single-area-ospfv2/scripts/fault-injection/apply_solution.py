#!/usr/bin/env python3
"""
Solution Restoration Script

Restores all devices to their correct OSPF configuration by pushing
the full solution configs from the solutions/ directory.
"""

from netmiko import ConnectHandler
from pathlib import Path
import argparse
import sys

# Device Console Mappings — ports are dynamic (from EVE-NG web UI / Console Access Table)
DEVICES = {
    "R1": 32768,
    "R2": 32769,
    "R3": 32770,
    "R4": 32771,
    "R5": 32772,
}

# Path to solution configs relative to this script
SOLUTIONS_DIR = Path(__file__).resolve().parent / ".." / ".." / "solutions"


def load_config(device_name):
    """Load and parse a solution config file, returning config lines."""
    cfg_path = SOLUTIONS_DIR / f"{device_name}.cfg"
    if not cfg_path.exists():
        print(f"[!] Solution file not found: {cfg_path}")
        return None

    lines = []
    for line in cfg_path.read_text().splitlines():
        stripped = line.strip()
        # Skip comments, blank lines, and the trailing 'end'
        if stripped == "" or stripped.startswith("!") or stripped == "end":
            continue
        lines.append(line)
    return lines


def restore_device(device_name, port, eve_ng_host):
    """Restore a single device to correct configuration."""
    print(f"\n[*] Restoring {device_name} ({eve_ng_host}:{port})...")

    config_lines = load_config(device_name)
    if config_lines is None:
        return False

    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=eve_ng_host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        print(f"[+] Connected to {device_name}")

        output = conn.send_config_set(config_lines)
        print(output)

        output = conn.save_config()
        print(output)

        print(f"[+] {device_name} restored successfully!")
        conn.disconnect()
        return True

    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {device_name} at {eve_ng_host}:{port}")
        print(f"[!] Make sure the EVE-NG lab is running and {device_name} is started.")
        return False
    except Exception as e:
        print(f"[!] Error on {device_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Restore all devices to solution state")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (default: 192.168.x.x)")
    args = parser.parse_args()

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for device_name, port in DEVICES.items():
        if restore_device(device_name, port, args.host):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"Restoration Complete: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)

    if fail_count > 0:
        print("[!] Some devices could not be restored. Verify EVE-NG lab is running.")
        sys.exit(1)
    else:
        print("[+] All devices restored to correct configuration!")
        print("[+] Lab is ready for normal operation.")


if __name__ == "__main__":
    main()
