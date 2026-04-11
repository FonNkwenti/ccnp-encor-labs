#!/usr/bin/env python3
"""
Fault Injection Script: Ticket 1 — Po1 Member Individual State

Injects:     Native VLAN mismatch on SW2 GigabitEthernet0/2
Target:      SW2
Fault Type:  Trunk Parameter Mismatch (Native VLAN)

Changes SW2 Gi0/2 native VLAN from 99 to 1, causing the Po1 member
to fall out of the bundle and show as 'I' (individual) in
show etherchannel summary on both SW1 and SW2.
"""

from netmiko import ConnectHandler
import sys

DEVICE_NAME  = "SW2"
EVE_NG_HOST  = "192.168.x.x"  # EVE-NG server IP — update to match your environment
CONSOLE_PORT = 32769           # Dynamic port from EVE-NG web UI / Console Access Table

FAULT_COMMANDS = [
    "interface GigabitEthernet0/2",
    "switchport trunk native vlan 1",
]


def inject_fault():
    """Connect to SW2 and inject the native VLAN mismatch fault."""
    print(f"[*] Connecting to {DEVICE_NAME} on {EVE_NG_HOST}:{CONSOLE_PORT}...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=EVE_NG_HOST,
            port=CONSOLE_PORT,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        print(f"[+] Connected to {DEVICE_NAME}.")
        print(f"[*] Injecting fault configuration...")
        output = conn.send_config_set(FAULT_COMMANDS)
        print(output)
        output = conn.save_config()
        print(output)
        conn.disconnect()
        print(f"[+] Fault injected successfully on {DEVICE_NAME}.")
        print(f"[!] Troubleshooting Scenario 1 is now active.")
    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {EVE_NG_HOST}:{CONSOLE_PORT}.")
        print(f"[!] Make sure the EVE-NG lab is running and {DEVICE_NAME} is started.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)
    inject_fault()
    print("=" * 60)
