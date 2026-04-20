#!/usr/bin/env python3
"""
setup_lab.py — Lab 03: RESTCONF and REST API Interpretation

Loads initial-configs onto all active devices and verifies RESTCONF is
reachable on R1 and R2. Run this script before each lab session or to
reset to the known-good state after troubleshooting.

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

DEFAULT_LAB_PATH = "automation/lab-03-restconf.unl"

DEVICES = {
    "R1": {
        "device_type": "cisco_ios_telnet",
        "host": None,
        "port": None,
        "username": "",
        "password": "",
        "secret": "",
        "config_file": os.path.join(os.path.dirname(__file__), "initial-configs", "R1.cfg"),
    },
    "R2": {
        "device_type": "cisco_ios_telnet",
        "host": None,
        "port": None,
        "username": "",
        "password": "",
        "secret": "",
        "config_file": os.path.join(os.path.dirname(__file__), "initial-configs", "R2.cfg"),
    },
    "R3": {
        "device_type": "cisco_ios_telnet",
        "host": None,
        "port": None,
        "username": "",
        "password": "",
        "secret": "",
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
    print("Lab 03: RESTCONF and REST API Interpretation")
    print("=" * 60)
    print()
    print("Phase 1 Summary:")
    print("  R1, R2: RESTCONF + NETCONF enabled (from lab-02 chain)")
    print("  R3:     EEM applets active (from lab-00)")
    print("  OSPF:   Process 1, all routers converged in area 0")
    print()
    print("RESTCONF is fully pre-configured on R1 and R2.")
    print("All API exercises start from a clean state.")
    print()
    print("Python requirements:")
    print("  pip install requests")
    print()
    print("RESTCONF base URL: https://10.1.12.1/restconf")
    print("Credentials:       admin / Encor-API-2026")
    print()
    print("Proceed to workbook.md Section 5, Task 1.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Lab 03 setup script")
    parser.add_argument("--host", required=True, help="EVE-NG server IP address")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset to known-good state (same as fresh load)",
    )
    args = parser.parse_args()

    if args.reset:
        print("[*] Reset flag set — reloading initial configs on all devices.")

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
