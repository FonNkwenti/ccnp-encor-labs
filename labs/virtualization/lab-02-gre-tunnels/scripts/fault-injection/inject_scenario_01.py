#!/usr/bin/env python3
"""
Fault Injection: Scenario 01

Target:     R4
Injects:    OSPF process 2 network statements moved from area 0 to area 1.
            The GRE tunnel comes UP (tunnel destination is still reachable via
            OSPF process 1), but no overlay routes appear in either router's
            routing table because the two OSPF neighbors are in different areas.
Fault Type: OSPF Area Mismatch on Overlay Process

Result:     R1 and R4 Tunnel0 interfaces show line protocol UP, but
            `show ip route ospf` on R1 shows no routes learned via Tunnel0.
            10.4.4.4/32 is unreachable. `show ip ospf neighbor` on Tunnel0
            shows no neighbors — area mismatch drops hellos before adjacency
            can form; there is no EXSTART or 2-way state.

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
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router ospf 2",
    "no network 172.16.14.0 0.0.0.3 area 0",
    "no network 10.4.4.4 0.0.0.0 area 0",
    "network 172.16.14.0 0.0.0.3 area 1",
    "network 10.4.4.4 0.0.0.0 area 1",
]
PREFLIGHT_CMD = "show running-config | section ospf 2"
PREFLIGHT_EXPECT = "area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print("[!] Pre-flight failed: R4 OSPF process 2 is not in the expected solution state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
