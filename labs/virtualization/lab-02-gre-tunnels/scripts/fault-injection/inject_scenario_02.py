#!/usr/bin/env python3
"""
Fault Injection: Scenario 02

Target:     R1
Injects:    Tunnel0 destination changed from 4.4.4.4 (R4 Lo0) to a
            non-existent IP 4.4.4.5. IOS cannot resolve a route to the
            new destination, so Tunnel0 line protocol drops to DOWN.
Fault Type: GRE Tunnel Destination Misconfiguration

Result:     R1 `show interfaces Tunnel0` shows line protocol DOWN.
            `show ip route` shows no overlay routes (tunnel is down).
            `show ip ospf neighbor` on R1 shows no neighbors via Tunnel0.
            The underlay (OSPF process 1) is unaffected -- R3 and R4 are
            still reachable via their physical interfaces.

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


DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-02-gre-tunnels.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface Tunnel0",
    "tunnel destination 4.4.4.5",
]
PREFLIGHT_CMD = "show running-config interface Tunnel0"
PREFLIGHT_EXPECT = "tunnel destination 4.4.4.4"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print("[!] Pre-flight failed: R1 Tunnel0 does not have the expected tunnel destination.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
