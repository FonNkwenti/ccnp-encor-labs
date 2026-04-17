#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- R1 VRRP IPv4 priority reduced below R2

Target:     R1
Injects:    Changes vrrp 1 address-family ipv4 priority from 110 to 90.
            R1's priority falls below R2's 100. Because preemption is on by
            default in VRRPv3, R2 immediately becomes VRRP Master for IPv4.
Symptom:    'show vrrp brief' on R1 shows Backup state for group 1 IPv4.
            R2 shows Master. PC1/PC2 IPv4 traffic routes through R2.
Teaches:    VRRP Master election is priority-based. Unlike HSRP, VRRPv3
            enables preemption by default -- any router with higher priority
            will immediately claim Master without waiting for the hold timer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-03-vrrp-dual-stack.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " vrrp 1 address-family ipv4",
    "  priority 90",
]
PREFLIGHT_CMD = "show vrrp brief"
PREFLIGHT_SOLUTION_MARKER = "Master"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R1 is not VRRP Master.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (R1 VRRP IPv4 priority reduced to 90)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 (R1 VRRP IPv4 priority 110 -> 90)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab {args.lab_path}.")
        return 3

    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
