#!/usr/bin/env python3
"""
setup_lab.py — Lab 04: Automation Capstone — Full Protocol Mastery

Loads clean-slate initial-configs onto all routers. Run before each lab
session to reset the environment to IP-only baseline (no OSPF, no APIs,
no EEM). The student configures everything from scratch.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>
    python3 setup_lab.py --host <eve-ng-ip> --reset
"""

import argparse
import sys
import os

try:
    from netmiko import ConnectHandler
except ImportError:
    print("[!] netmiko not installed. Run: pip install netmiko")
    sys.exit(1)

DEFAULT_LAB_PATH = "automation/lab-04-capstone-config.unl"

DEVICES = {
    "R1": {
        "device_type": "cisco_ios_telnet",
        "config_file": os.path.join(os.path.dirname(__file__), "initial-configs", "R1.cfg"),
    },
    "R2": {
        "device_type": "cisco_ios_telnet",
        "config_file": os.path.join(os.path.dirname(__file__), "initial-configs", "R2.cfg"),
    },
    "R3": {
        "device_type": "cisco_ios_telnet",
        "config_file": os.path.join(os.path.dirname(__file__), "initial-configs", "R3.cfg"),
    },
}

CONSOLE_PORTS = {
    "R1": None,
    "R2": None,
    "R3": None,
}


def load_config(host, port, device_name, config_file):
    if not os.path.exists(config_file):
        print(f"[!] Config file not found: {config_file}")
        return False

    with open(config_file) as f:
        commands = [line.rstrip() for line in f if line.strip() and not line.startswith("!")]

    print(f"[*] Connecting to {device_name} on {host}:{port}...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=15,
        )
        print(f"[+] Connected. Loading config onto {device_name}...")
        conn.send_command("enable")
        conn.send_command("configure terminal")
        for cmd in commands:
            conn.send_command(cmd, expect_string=r"[#(]")
        conn.send_command("end")
        conn.send_command("write memory")
        conn.disconnect()
        print(f"[+] {device_name} configured.")
        return True
    except Exception as e:
        print(f"[!] Error on {device_name}: {e}")
        return False


def print_summary():
    print()
    print("=" * 60)
    print("Lab 04: Automation Capstone — Full Protocol Mastery")
    print("=" * 60)
    print()
    print("Clean-slate baseline loaded:")
    print("  R1, R2, R3: IP addressing only")
    print("  No OSPF, no SSH, no NETCONF, no RESTCONF, no EEM")
    print()
    print("Your tasks:")
    print("  1. OSPF underlay (all 3 routers, area 0)")
    print("  2. SSH hardening (all 3 routers)")
    print("  3. NETCONF on R1 and R2")
    print("  4. RESTCONF on R1 and R2")
    print("  5. Python NETCONF script (ncclient)")
    print("  6. Python RESTCONF script (requests)")
    print("  7. EEM applets on R3")
    print("  8. JSON payload construction")
    print()
    print("Python requirements:")
    print("  pip install ncclient requests netmiko")
    print()
    print("Proceed to workbook.md Section 5.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Lab 04 setup script")
    parser.add_argument("--host", required=True, help="EVE-NG server IP address")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset to clean-slate baseline (same as fresh load)",
    )
    args = parser.parse_args()

    if args.reset:
        print("[*] Reset flag set — reloading clean-slate configs on all devices.")

    eve_host = args.host

    missing_ports = [d for d, p in CONSOLE_PORTS.items() if p is None]
    if missing_ports:
        print("[!] Console ports not configured for:", ", ".join(missing_ports))
        print("    Update CONSOLE_PORTS in this script with ports from the EVE-NG web UI.")
        print("    Example: CONSOLE_PORTS = {'R1': 32768, 'R2': 32769, 'R3': 32770}")
        sys.exit(1)

    results = []
    for device_name, port in CONSOLE_PORTS.items():
        cfg = DEVICES[device_name]["config_file"]
        ok = load_config(eve_host, port, device_name, cfg)
        results.append((device_name, ok))

    print()
    failed = [d for d, ok in results if not ok]
    if failed:
        print(f"[!] Setup incomplete. Failed devices: {', '.join(failed)}")
        sys.exit(1)

    print("[+] All devices configured successfully.")
    print_summary()


if __name__ == "__main__":
    main()
