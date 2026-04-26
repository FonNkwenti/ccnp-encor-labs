#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Po2 Down Between SW1 and SW3

Target:     SW3 (all EtherChannel members)
Injects:    EtherChannel protocol mismatch on ALL SW3 bundles:
              Po2 (Gi0/3, Gi1/0): PAgP 'auto' → LACP 'active'
                  SW1 remains PAgP 'desirable' → protocol mismatch, no bundle.
              Po3 (Gi0/1, Gi0/2): static 'on' → LACP 'passive'
                  SW2 remains static 'on' → static vs LACP, no bundle.
Fault Type: EtherChannel Protocol Mismatch (PAgP vs LACP on Po2;
                                            static vs LACP on Po3)

Result:     Both SW3 uplinks (Po2 and Po3) go down, completely isolating
            SW3 and PC2 from the campus. Faulting only Po2 leaves an
            alternate path via Po3 (SW2-SW3) in the triangular mesh,
            so both bundles must be broken to produce the expected symptom.

Two-phase injection: all 'no channel-group' removals are sent first, then
a 3-second pause allows IOS log messages to flush before the new
channel-group modes are applied. Interleaving removes and re-adds in a
single send_config_set causes Netmiko to lose prompt sync mid-set.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-01-etherchannel.unl"
DEVICE_NAME = "SW3"
# Phase 1: remove all channel-group memberships
FAULT_COMMANDS_REMOVE = [
    "interface GigabitEthernet0/3", "no channel-group",
    "interface GigabitEthernet1/0", "no channel-group",
    "interface GigabitEthernet0/1", "no channel-group",
    "interface GigabitEthernet0/2", "no channel-group",
]
# Phase 2: apply new (fault) modes
FAULT_COMMANDS_ADD = [
    # Po2: LACP active — mismatches SW1's PAgP desirable
    "interface GigabitEthernet0/3", "channel-group 2 mode active",
    "interface GigabitEthernet1/0", "channel-group 2 mode active",
    # Po3: LACP passive — mismatches SW2's static on; eliminates bypass path
    "interface GigabitEthernet0/1", "channel-group 3 mode passive",
    "interface GigabitEthernet0/2", "channel-group 3 mode passive",
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
        print("[*] Phase 1: removing channel-group memberships ...")
        conn.send_config_set(FAULT_COMMANDS_REMOVE, cmd_verify=False)
        print("[*] Waiting for IOS to flush topology change messages ...")
        time.sleep(3)
        print("[*] Phase 2: applying fault modes ...")
        conn.send_config_set(FAULT_COMMANDS_ADD, cmd_verify=False)
        time.sleep(5)   # let IOS finish emitting topology-change syslog
        conn.clear_buffer()
        conn.send_command_timing("write memory", read_timeout=30)
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
