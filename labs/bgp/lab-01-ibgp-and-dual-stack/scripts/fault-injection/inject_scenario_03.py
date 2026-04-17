#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- R1 Missing IPv6 network Advertisement

Target:     R1
Injects:    'no network 2001:DB8:172:1::/64' under router bgp 65001
            address-family ipv6.
Symptom:    R1's IPv4 BGP table still carries 172.16.1.0/24 and
            192.168.1.0/24 (v4 networks untouched). R1's IPv6 BGP table is
            missing the 2001:DB8:172:1::/64 entry. R3 does not receive the
            prefix via eBGP, even though R1's Loopback1 is up and correctly
            addressed.
Teaches:    The 'network' statement under each address-family injects
            ONLY the prefix listed there. IPv4 and IPv6 are independent:
            you must advertise each family's prefixes separately, and the
            route must exist in the corresponding unicast RIB.

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


DEFAULT_LAB_PATH = "bgp/lab-01-ibgp-and-dual-stack.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router bgp 65001",
    " address-family ipv6",
    "  no network 2001:DB8:172:1::/64",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "network 2001:DB8:172:1::/64"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R1 does not have 'network 2001:DB8:172:1::/64' under IPv6 AF.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (R1 missing v6 network statement)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (R1 missing IPv6 network statement)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
