#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Missing MED Outbound Route-Map on R3 to R2

Target:     R3
Injects:    'no neighbor 10.0.23.1 route-map MED_TO_R2 out' under router
            bgp 65002 IPv4 address-family.
Symptom:    R1 still sees Metric 50 on its direct eBGP-learned paths from
            R3 (LocPref 200 wins anyway, so path selection is unaffected).
            R2 sees Metric 0 on its own eBGP path from R3 (the MED was
            never applied outbound), breaking the documented policy that
            R2 should receive MED 100.
Teaches:    Outbound route-maps must be applied per-neighbor, on the
            sending router. The route-map definition staying intact often
            hides the real problem -- 'show ip bgp neighbors X policy'
            is the fastest way to confirm what is actually attached.

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
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router bgp 65002",
    " address-family ipv4",
    "  no neighbor 10.0.23.1 route-map MED_TO_R2 out",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "neighbor 10.0.23.1 route-map MED_TO_R2 out"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: MED_TO_R2 not applied outbound on 10.0.23.1.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (missing MED outbound on R3 toward R2)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (R3 missing outbound MED route-map to R2)")
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
        conn.send_command_timing("clear ip bgp 10.0.23.1 soft out")
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
