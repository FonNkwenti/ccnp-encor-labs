#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Missing next-hop-self on R2

Target:     R2
Injects:    Removes 'neighbor 1.1.1.1 next-hop-self' from router bgp 65001
            IPv4 address-family.
Symptom:    iBGP session R1<->R2 stays Established. R2 learns 172.16.3.0/24
            from R3 and propagates it to R1, but the NEXT_HOP attribute
            still carries R3's eBGP peering address (10.0.23.2). R1 has no
            IGP route to 10.0.23.2, so the prefix is received but marked
            inaccessible -- no RIB install, no ping.
Teaches:    iBGP does not rewrite NEXT_HOP by default. On an iBGP peering
            that carries eBGP-learned prefixes, 'next-hop-self' is almost
            always required, OR the eBGP transit subnet must be in the IGP.

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
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router bgp 65001",
    " address-family ipv4",
    "  no neighbor 1.1.1.1 next-hop-self",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "neighbor 1.1.1.1 next-hop-self"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R2 does not have 'neighbor 1.1.1.1 next-hop-self'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (missing next-hop-self on R2)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 (R2 missing next-hop-self)")
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
