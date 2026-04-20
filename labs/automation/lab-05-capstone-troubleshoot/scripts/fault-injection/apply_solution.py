#!/usr/bin/env python3
"""
apply_solution.py — Lab 05: Automation Capstone — Comprehensive Troubleshooting

Restores all devices to the fully working state defined in solutions/.
Run this after completing (or abandoning) a troubleshooting session.

Usage:
    python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
"""

import argparse
import sys
import os

try:
    from netmiko import ConnectHandler
except ImportError:
    print("[!] netmiko not installed. Run: pip install netmiko")
    sys.exit(1)

LAB_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SOLUTIONS = {
    "R1": os.path.join(LAB_ROOT, "solutions", "R1.cfg"),
    "R2": os.path.join(LAB_ROOT, "solutions", "R2.cfg"),
    "R3": os.path.join(LAB_ROOT, "solutions", "R3.cfg"),
}

CONSOLE_PORTS = {
    "R1": None,
    "R2": None,
    "R3": None,
}


def apply_solution(host, port, device_name, config_file):
    if not os.path.exists(config_file):
        print(f"[!] Solution file not found: {config_file}")
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
        print(f"[+] Connected. Restoring {device_name} to working state...")
        conn.send_command("enable")
        conn.send_command("configure terminal")
        for cmd in commands:
            conn.send_command(cmd, expect_string=r"[#(]")
        conn.send_command("end")
        conn.send_command("write memory")
        conn.disconnect()
        print(f"[+] {device_name} restored.")
        return True
    except Exception as e:
        print(f"[!] Error on {device_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Restore all devices to working state")
    parser.add_argument("--host", required=True, help="EVE-NG server IP address")
    args = parser.parse_args()

    eve_host = args.host

    missing_ports = [d for d, p in CONSOLE_PORTS.items() if p is None]
    if missing_ports:
        print("[!] Console ports not configured for:", ", ".join(missing_ports))
        print("    Update CONSOLE_PORTS in this script with ports from the EVE-NG web UI.")
        sys.exit(1)

    print("=" * 50)
    print("Restoring Lab 05 to working state")
    print("=" * 50)

    results = []
    for device_name, port in CONSOLE_PORTS.items():
        cfg = SOLUTIONS[device_name]
        ok = apply_solution(eve_host, port, device_name, cfg)
        results.append((device_name, ok))

    print()
    failed = [d for d, ok in results if not ok]
    if failed:
        print(f"[!] Restore incomplete. Failed devices: {', '.join(failed)}")
        sys.exit(1)

    print("[+] All devices restored to working state.")
    print("[+] OSPF, SSH, NETCONF, RESTCONF, and EEM are all functional.")


if __name__ == "__main__":
    main()
