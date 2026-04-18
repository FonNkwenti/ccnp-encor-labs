#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Po3 Entire Bundle Down

Target:     SW3 (all EtherChannel members)
Injects:    EtherChannel mode mismatch on ALL SW3 bundles:
              Po3 (Gi0/1, Gi0/2): static 'on' → LACP 'passive'
                  SW2 remains static 'on' → neither side speaks, no bundle.
              Po2 (Gi0/3, Gi1/0): PAgP 'auto' → static 'on'
                  SW1 remains PAgP 'desirable' → static vs PAgP, no bundle.
Fault Type: EtherChannel Mode Mismatch (static vs LACP on Po3;
                                        static vs PAgP on Po2)

Result:     Both SW3 uplinks (Po3 and Po2) go down, completely isolating
            SW3 and PC2. Faulting only Po3 leaves an alternate path via
            Po2 (SW1-SW3) in the triangular mesh, so both bundles must be
            broken to produce the expected symptom.

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
    # Po3 fault: static on → LACP passive (static/LACP mismatch with SW2 mode on)
    "interface GigabitEthernet0/1",
    "no channel-group 3",
    "channel-group 3 mode passive",
    "interface GigabitEthernet0/2",
    "no channel-group 3",
    "channel-group 3 mode passive",
    # Po2 fault: PAgP auto → static on (eliminates bypass via SW1-SW3)
    "interface GigabitEthernet0/3",
    "no channel-group 2",
    "channel-group 2 mode on",
    "interface GigabitEthernet1/0",
    "no channel-group 2",
    "channel-group 2 mode on",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/1"
# Solution state has static 'mode on' on SW3's Po3 members
PREFLIGHT_EXPECT = "channel-group 3 mode on"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: Gi0/1 does not have '{PREFLIGHT_EXPECT}'.")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
