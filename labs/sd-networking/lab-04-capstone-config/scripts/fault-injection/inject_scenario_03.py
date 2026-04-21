#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- vSmart Apply-Policy Removal

Target:     vSmart
Platform:   Viptela 20.6.2

Before running, ensure the lab is in the solution state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys

from netmiko import ConnectHandler

DEFAULT_EVE_NG_HOST = "192.168.x.x"

# Telnet port assigned to vSmart in EVE-NG UI -- update before use
VSMART_PORT = 0

FAULT_COMMANDS = [
    "no apply-policy",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject Scenario 03 fault onto vSmart"
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_EVE_NG_HOST,
        help="EVE-NG server IP (default: %(default)s)",
    )
    return parser.parse_args()


def inject(eve_ng_host: str) -> int:
    print("=" * 60)
    print("Fault Injection: Scenario 03")
    print("=" * 60)

    device = {
        "device_type": "cisco_ios_telnet",
        "host": eve_ng_host,
        "port": VSMART_PORT,
        "username": "admin",
        "password": "admin",
        "config_mode_command": "config",
        "cmd_verify": False,
        "exit_config_mode": False,
    }

    print(f"[*] Connecting to vSmart on {eve_ng_host}:{VSMART_PORT} ...")
    try:
        conn = ConnectHandler(**device)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS)
        conn.send_command("commit")
    finally:
        conn.disconnect()

    print("[+] Fault injected on vSmart. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(inject(args.host))
