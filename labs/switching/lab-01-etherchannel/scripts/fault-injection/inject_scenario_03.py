#!/usr/bin/env python3
"""
Fault Injection Script: Ticket 3 — Po3 Entire Bundle Down

Injects:     Static/LACP mode mismatch on SW3 Po3 members — changes
             Gi0/1 and Gi0/2 from mode on to LACP passive
Target:      SW3
Fault Type:  EtherChannel Mode Mismatch (static vs LACP)

SW2 continues to run static mode (mode on) on its Po3 members (Gi0/3,
Gi1/0). Changing SW3 to LACP passive means neither side initiates
LACP negotiation, and static/LACP is incompatible — Po3 goes down
entirely, making SW3 unreachable from SW2.

IOS requires removing the channel-group membership before changing
protocols; commands are ordered accordingly.
"""

from netmiko import ConnectHandler
import sys

DEVICE_NAME  = "SW3"
EVE_NG_HOST  = "192.168.x.x"  # EVE-NG server IP — update to match your environment
CONSOLE_PORT = 32770           # Dynamic port from EVE-NG web UI / Console Access Table

FAULT_COMMANDS = [
    "interface GigabitEthernet0/1",
    "no channel-group 3",
    "channel-group 3 mode passive",
    "interface GigabitEthernet0/2",
    "no channel-group 3",
    "channel-group 3 mode passive",
]


def inject_fault():
    """Connect to SW3 and inject the Po3 mode mismatch fault."""
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
        print(f"[!] Troubleshooting Scenario 3 is now active.")
    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {EVE_NG_HOST}:{CONSOLE_PORT}.")
        print(f"[!] Make sure the EVE-NG lab is running and {DEVICE_NAME} is started.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Fault Injection: Scenario 03")
    print("=" * 60)
    inject_fault()
    print("=" * 60)
