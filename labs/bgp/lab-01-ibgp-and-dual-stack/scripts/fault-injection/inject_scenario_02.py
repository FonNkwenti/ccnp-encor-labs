#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- R1 iBGP-IPv6 Neighbor Administratively Shut

Target:     R1
Injects:    'neighbor 2001:DB8:FF::2 shutdown' under router bgp 65001.
Symptom:    IPv4 iBGP session R1<->R2 is Established (still fine).
            IPv6 BGP session to 2001:DB8:FF::2 transitions to Idle (Admin)
            and stays there. R2 does not learn R3's IPv6 prefixes via iBGP;
            R1 does not learn R2's eBGP-v6 receptions. Dual-stack is broken
            for IPv6 only.
Teaches:    BGP runs a *session per neighbor* under a single 'router bgp'
            process. An admin shutdown is scoped to that one neighbor --
            'show bgp ipv6 unicast summary' reveals Idle (Admin) for the
            affected peer while other sessions continue normally.

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
    " neighbor 2001:DB8:FF::2 shutdown",
]
PREFLIGHT_CMD = "show bgp ipv6 unicast summary | include 2001:DB8:FF::2"
PREFLIGHT_SOLUTION_MARKER = "2001:DB8:FF::2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: iBGP IPv6 neighbor 2001:DB8:FF::2 not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (admin shutdown on R1 iBGP-IPv6 peer)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (R1 iBGP-IPv6 neighbor shutdown)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
