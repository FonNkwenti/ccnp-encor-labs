#!/usr/bin/env python3
"""
Solution Restoration Script

Restores all devices to their correct configuration by pushing
the full solution configs from the solutions/ directory.

This script reads each device's .cfg file and applies it via
Netmiko, removing all injected faults from troubleshooting scenarios.
"""

from netmiko import ConnectHandler
from pathlib import Path
import argparse
import re
import sys

# Path to solutions directory (relative to this script)
SOLUTIONS_DIR = Path(__file__).resolve().parent.parent.parent / "solutions"

# Device Console Mappings — ports are dynamic (from EVE-NG web UI / Console Access Table)
DEVICES = {
    "SW1": {"port": 32768, "config_file": "SW1.cfg"},
    "SW2": {"port": 32769, "config_file": "SW2.cfg"},
    "SW3": {"port": 32770, "config_file": "SW3.cfg"},
    "R1":  {"port": 32771, "config_file": "R1.cfg"},
}


def parse_config(config_text):
    """Extract configuration commands from a .cfg file.

    Strips comment lines, blank lines, and IOS markers (end, !).
    Returns a flat list of commands suitable for send_config_set().
    """
    commands = []
    for line in config_text.splitlines():
        stripped = line.rstrip()
        # Skip empty lines, comments, the 'end' marker, and bare '!'
        if not stripped or stripped.startswith("!") or stripped.lower() == "end":
            continue
        commands.append(stripped)
    return commands


def restore_device(device_name, eve_ng_host):
    """Restore a single device to its solution configuration."""
    info = DEVICES[device_name]
    port = info["port"]
    config_path = SOLUTIONS_DIR / info["config_file"]

    print(f"\n[*] Restoring {device_name} ({eve_ng_host}:{port})...")

    if not config_path.exists():
        print(f"[!] Solution config not found: {config_path}")
        return False

    config_text = config_path.read_text(encoding="utf-8")
    commands = parse_config(config_text)

    if not commands:
        print(f"[!] No commands parsed from {config_path}")
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

        output = conn.send_config_set(commands)
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
    parser = argparse.ArgumentParser(
        description="Restore all devices to solution configuration"
    )
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (default: 192.168.x.x)")
    args = parser.parse_args()

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)
    print(f"[*] Solutions directory: {SOLUTIONS_DIR}")

    success_count = 0
    fail_count = 0

    for device_name in DEVICES:
        if restore_device(device_name, args.host):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"Restoration Complete: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)

    if fail_count > 0:
        print("[!] Some devices could not be restored. Check EVE-NG lab status.")
        sys.exit(1)
    else:
        print("[+] All devices restored to correct configuration!")
        print("[+] Lab is ready for normal operation.")


if __name__ == "__main__":
    main()
