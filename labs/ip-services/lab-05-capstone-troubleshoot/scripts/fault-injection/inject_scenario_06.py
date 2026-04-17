#!/usr/bin/env python3
"""
Fault Injection: Scenario 06 -- R3 OSPF passive-interface blocks R1-R3 adjacency

Target:     R3
Injects:    Adds 'passive-interface GigabitEthernet0/0' to both OSPFv2 and
            OSPFv3 on R3. R3 stops sending/receiving OSPF Hellos toward R1.
            The R1-R3 adjacency drops. R1 loses route to 203.0.113.1.
Symptom:    'show ip ospf neighbor' on R1 shows only R2 (via Gi0/0 and Gi0/2).
            R1 has no route to 10.0.13.2 or 203.0.113.1. NAT translations to
            the internet server fail. R3 still has full adjacency with R2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router ospf 1",
    " passive-interface GigabitEthernet0/0",
    "ipv6 router ospf 1",
    " passive-interface GigabitEthernet0/0",
]
PREFLIGHT_CMD = "show ip ospf neighbor"
PREFLIGHT_SOLUTION_MARKER = "1.1.1.1"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R3 has no adjacency with R1 (1.1.1.1).")
        print("    Run apply_solution.py first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 06 (R3 OSPF passive on Gi0/0)")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    host = require_host(args.host)
    print("=" * 60)
    print("Fault Injection: Scenario 06 (R3 OSPF passive on Gi0/0)")
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
    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 06 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
