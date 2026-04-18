#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- K-value Mismatch on R1 (IPv4)

Target:     R1
Injects:    `metric weights 0 2 0 1 0 0` under R1's IPv4 AF.
            K1 changes from 1 to 2 while R2 and R3 still run defaults.
            R1 rejects every IPv4 hello as a K-value mismatch.
            IPv6 adjacencies are unaffected (IPv6 AF keeps default K-values).
Teaches:    K-values must match on both neighbors, per AF in named mode.
            Syslog floods with %DUAL-5-NBRCHANGE ... K-value mismatch.

Before running, ensure the lab is in the solution state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "eigrp/lab-04-capstone-troubleshoot.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router eigrp EIGRP-LAB",
    " address-family ipv4 unicast autonomous-system 100",
    "  metric weights 0 2 0 1 0 0",
    " exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router eigrp"
PREFLIGHT_SOLUTION_MARKER = "eigrp router-id 1.1.1.1"
# Reject if R1 already has non-default K-values
PREFLIGHT_ALREADY_BROKEN_MARKER = "metric weights"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R1 missing expected EIGRP config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_ALREADY_BROKEN_MARKER in output:
        print(f"[!] Pre-flight: R1 already has 'metric weights' configured.")
        print("    The fault may already be injected. Run apply_solution.py to reset first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (K-value mismatch on R1)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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
