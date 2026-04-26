#!/usr/bin/env python3
"""
Fault Injection: Scenario 05 -- R2 VRRPv3 IPv6 address-family removed

Target:     R2
Injects:    Removes the 'vrrp 1 address-family ipv6' block from R2 Gi0/0.
            R2 has no IPv6 VRRP backup. On R1 failure, IPv6 hosts lose
            their default gateway with no automatic failover.
Symptom:    'show vrrp' on R2 shows only IPv4 address-family for group 1.
            After shutting R1 Gi0/0, PC IPv6 traffic has no gateway.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no vrrp 1 address-family ipv6",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "address-family ipv6"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R2 Gi0/0 does not have VRRPv3 IPv6 AF.")
        print("    Run apply_solution.py first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 05 (R2 VRRPv3 IPv6 AF removed)")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    host = require_host(args.host)
    print("=" * 60)
    print("Fault Injection: Scenario 05")
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
    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 05 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
