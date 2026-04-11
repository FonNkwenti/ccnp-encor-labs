#!/usr/bin/env python3
"""
Fault Injection Script: Missing Network Statement

Injects:     Removes OSPF network statement for PC1 LAN from R4
Target:      R4
Fault Type:  Route Advertisement Error
"""

from netmiko import ConnectHandler
import argparse
import sys

# Device Configuration
DEVICE_NAME = "R4"
CONSOLE_PORT = 32771  # Dynamic port from EVE-NG web UI / Console Access Table

# Fault Configuration Commands
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 192.168.1.0 0.0.0.255 area 0",
]


def inject_fault(eve_ng_host):
    """Connect to device and inject the fault configuration."""
    print(f"[*] Connecting to {DEVICE_NAME} on {eve_ng_host}:{CONSOLE_PORT}...")

    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=eve_ng_host,
            port=CONSOLE_PORT,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        print(f"[+] Connected to {DEVICE_NAME}")

        print(f"[*] Injecting fault configuration...")
        output = conn.send_config_set(FAULT_COMMANDS)
        print(output)

        output = conn.save_config()
        print(output)

        conn.disconnect()

        print(f"[+] Fault injected successfully on {DEVICE_NAME}!")

    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {eve_ng_host}:{CONSOLE_PORT}")
        print(f"[!] Make sure the EVE-NG lab is running and {DEVICE_NAME} is started.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (default: 192.168.x.x)")
    args = parser.parse_args()

    print("=" * 60)
    print("Fault Injection: Scenario 02")
    print("=" * 60)
    inject_fault(args.host)
    print("=" * 60)
