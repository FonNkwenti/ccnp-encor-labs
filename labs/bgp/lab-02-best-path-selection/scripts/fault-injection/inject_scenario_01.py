#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Missing LOCAL_PREF Inbound Route-Map on R1

Target:     R1
Injects:    'no neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in' under
            router bgp 65001 IPv4 address-family.
Symptom:    iBGP and eBGP sessions are all Established. R1 still receives
            all prefixes. But LocPref is 100 (default) on R1's eBGP path
            instead of 200, so traffic from AS 65001 toward R4's networks
            can leave via either R1 or R2. Downstream (R2) sees its own
            eBGP path winning because R1's LocPref 200 advertisement is
            gone.
Teaches:    A route-map that exists but is NOT applied has no effect.
            'show route-map NAME' shows 0 hits -- the definition is fine;
            the application is missing. Always verify both the definition
            AND the per-neighbor attachment.

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


DEFAULT_LAB_PATH = "bgp/lab-02-best-path-selection.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router bgp 65001",
    " address-family ipv4",
    "  no neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: LOCAL_PREF_FROM_R3 not applied inbound on 10.0.13.2.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (missing LOCAL_PREF inbound on R1)")
    parser.add_argument("--host", default="192.168.1.214",
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
        conn.send_command_timing("clear ip bgp 10.0.13.2 soft in")
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
