#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- R1 NAT inside/outside interfaces reversed

Target:     R1
Injects:    Moves 'ip nat inside' to Gi0/1 (uplink) and 'ip nat outside' to
            Gi0/0 (LAN). NAT processes traffic from the wrong direction.
Symptom:    No translations in 'show ip nat translations'. PC1/PC2 cannot
            reach 203.0.113.1. Static NAT entry for PC1 is present but unused.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no ip nat inside",
    " ip nat outside",
    "interface GigabitEthernet0/1",
    " no ip nat outside",
    " ip nat inside",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "ip nat inside"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R1 Gi0/0 does not have 'ip nat inside'.")
        print("    Run apply_solution.py first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (R1 NAT inside/outside reversed)")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    host = require_host(args.host)
    print("=" * 60)
    print("Fault Injection: Scenario 01 (R1 NAT interfaces reversed)")
    print("=" * 60)
    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3
    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found.")
        return 3
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3
    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()
    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
