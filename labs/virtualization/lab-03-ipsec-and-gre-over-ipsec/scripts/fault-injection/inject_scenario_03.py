#!/usr/bin/env python3
"""
Fault Injection: Scenario 03

Target:     R4
Injects:    OSPF process 3 network statement for the Loopback6 address
            (10.4.4.6/32) removed from R4. OSPF process 3 adjacency on
            Tunnel2 remains FULL, but R4 does not originate an LSA for
            that prefix so R1 never learns the route.
Fault Type: Missing OSPF Route Advertisement

Result:     `show ip ospf 3 neighbor` on R1 shows R4 in FULL state.
            `show ip route 10.4.4.6` on R1 returns no match.
            `show ip ospf 3 database` shows no type-1 LSA for 10.4.4.6.
            `show running-config | section ospf 3` on R4 lacks the
            network statement for 10.4.4.6.
            Tunnel1, Tunnel2 line protocol, and OSPF 3 neighbor state are
            unaffected; only the prefix advertisement is missing.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-03-ipsec-and-gre-over-ipsec.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router ospf 3",
    "no network 10.4.4.6 0.0.0.0 area 0",
]
PREFLIGHT_CMD = "show running-config | section ospf 3"
PREFLIGHT_EXPECT = "10.4.4.6"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print("[!] Pre-flight failed: OSPF process 3 does not contain the expected network statement.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print("[+] Fault injected. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
