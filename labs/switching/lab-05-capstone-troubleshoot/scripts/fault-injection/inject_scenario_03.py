#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- EtherChannel Protocol Mismatch on Po2

Target:     SW3 Gi0/3 (one member of Po2)
Injects:    Replaces 'channel-group 2 mode auto' (PAgP) with
            'channel-group 2 mode passive' (LACP) on a single member.
            The other SW3 member (Gi1/0) stays on PAgP auto, and SW1
            is PAgP desirable. LACP and PAgP cannot bundle together.
Fault Type: EtherChannel mode / protocol mismatch

Result:     - `show etherchannel summary` reports Po2 as (SD) on SW1/SW3.
            - Members go to (s) suspended -- one runs LACP, the others
              run PAgP, no bundle forms.
            - %EC-5-CANNOT_BUNDLE2 syslog messages on SW3.
            - PC2 reachability relies on the Po1->Po3 detour path.

Before running, ensure the lab is in the SOLUTION state:
    python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/3",
    "no channel-group 2 mode auto",
    "channel-group 2 mode passive",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/3"
PREFLIGHT_SOLUTION_MARKER = "channel-group 2 mode auto"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Gi0/3 is missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: 192.168.242.128)")
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
