#!/usr/bin/env python3
"""
Fault Injection Script: Scenario 02 — Native VLAN Mismatch

Injects:     Changes native VLAN on SW2 Gi0/1 trunk back to VLAN 1
Target:      SW2
Fault Type:  Native VLAN Mismatch
"""

from netmiko import ConnectHandler
import argparse
import sys

# Device Configuration
DEVICE_NAME = "SW2"
CONSOLE_PORT = 32769  # Dynamic port from EVE-NG web UI — replace with actual port

# Fault Configuration Commands
FAULT_COMMANDS = [
    "interface GigabitEthernet0/1",
    "switchport trunk native vlan 1",
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
        print(f"[!] Troubleshooting Scenario 02 is now active.")

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
