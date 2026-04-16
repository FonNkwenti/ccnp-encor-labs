#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Po2 Down Between SW1 and SW3

Target:     SW3 (Gi0/3, Gi1/0 -- Po2 members to SW1)
Injects:    EtherChannel protocol mismatch -- changes SW3 members from
            PAgP 'auto' to LACP 'active' (SW1 remains PAgP 'desirable')
Fault Type: EtherChannel Protocol Mismatch (PAgP vs LACP)

Result:     No bundle forms between SW1 and SW3. Po2 goes down and the
            VLAN 20 / PC2 segment becomes isolated from the rest of the
            campus.

IOS requires removing the channel-group membership before changing the
mode to a different protocol family; commands are ordered accordingly.

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-01-etherchannel.unl"
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/3",
    "no channel-group 2",
    "channel-group 2 mode active",
    "interface GigabitEthernet1/0",
    "no channel-group 2",
    "channel-group 2 mode active",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/3"
# Solution state uses PAgP auto on SW3's Po2 members
PREFLIGHT_EXPECT = "channel-group 2 mode auto"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: Gi0/3 does not have '{PREFLIGHT_EXPECT}'.")
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
    print("Fault Injection: Scenario 02 (Po2 Protocol Mismatch PAgP/LACP)")
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
