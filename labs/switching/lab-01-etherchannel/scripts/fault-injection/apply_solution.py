#!/usr/bin/env python3
"""
Solution Restoration Script — Lab 01: Static and Dynamic EtherChannels

Restores all affected devices to their correct known-good configuration,
removing all injected faults from troubleshooting scenarios.

Affected devices:
  SW2 — restores Gi0/2 native VLAN to 99 (Ticket 1 fix)
  SW3 — restores Po2 members to PAgP auto (Ticket 2 fix)
         restores Po3 members to static mode on (Ticket 3 fix)

SW1 and R1 are never faulted by any inject script and are not touched.
"""

from netmiko import ConnectHandler
import sys

# EVE-NG server IP — update to match your environment
EVE_NG_HOST = "192.168.x.x"

# Device console port mappings (dynamic — from EVE-NG web UI / Console Access Table)
DEVICES = {
    "SW2": {"host": EVE_NG_HOST, "port": 32769},
    "SW3": {"host": EVE_NG_HOST, "port": 32770},
}

# Correct configurations per device — derived from solutions/ directory
CONFIGS = {
    "SW2": [
        # Restore Gi0/2 native VLAN to 99 (fixes Ticket 1)
        "interface GigabitEthernet0/2",
        "switchport trunk native vlan 99",
    ],
    "SW3": [
        # Restore Po2 members from LACP active to PAgP auto (fixes Ticket 2)
        # IOS requires removing channel-group before changing protocols
        "interface GigabitEthernet0/3",
        "no channel-group 2",
        "channel-group 2 mode auto",
        "interface GigabitEthernet1/0",
        "no channel-group 2",
        "channel-group 2 mode auto",
        # Restore Po3 members from LACP passive to static mode on (fixes Ticket 3)
        "interface GigabitEthernet0/1",
        "no channel-group 3",
        "channel-group 3 mode on",
        "interface GigabitEthernet0/2",
        "no channel-group 3",
        "channel-group 3 mode on",
    ],
}


def restore_device(device_name, config):
    """Restore a single device to its correct solution configuration."""
    host = DEVICES[device_name]["host"]
    port = DEVICES[device_name]["port"]

    print(f"\n[*] Restoring {device_name} ({host}:{port})...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        print(f"[+] Connected to {device_name}.")
        output = conn.send_config_set(config)
        print(output)
        output = conn.save_config()
        print(output)
        conn.disconnect()
        print(f"[+] {device_name} restored successfully.")
        return True
    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {device_name} at {host}:{port}.")
        print(f"[!] Make sure the EVE-NG lab is running and {device_name} is started.")
        return False
    except Exception as e:
        print(f"[!] Error on {device_name}: {e}")
        return False


def main():
    """Restore all affected devices to their correct configuration."""
    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for device_name, config in CONFIGS.items():
        if restore_device(device_name, config):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"Restoration Complete: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)

    if fail_count > 0:
        print("[!] Some devices could not be restored. Verify EVE-NG lab is running and try again.")
        sys.exit(1)
    else:
        print("[+] All devices restored to correct configuration.")
        print("[+] Lab is ready for the next troubleshooting scenario.")


if __name__ == "__main__":
    main()
