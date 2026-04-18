#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- BPDU Guard Err-Disables SW3 Gi1/1 (PC2 port)

Target:     SW3 GigabitEthernet1/1 (PC2 access port, VLAN 20)
Injects:    In the real world, a BPDU arriving on a PortFast access port
            with 'spanning-tree bpduguard enable' causes the port to
            transition to state 'err-disabled (bpduguard)'. Reproducing
            that exact condition in EVE-NG requires cabling a second
            switch (BPDU source) into Gi1/1, which is not portable across
            fresh imports of the .unl.

            --- Simulation used here ---
            We shut the port down so the interface enters administratively-
            down state. The student workflow ("diagnose why PC2 can't
            reach its gateway, then bounce the port with shutdown /
            no shutdown") is identical for a real err-disabled port and
            an admin-down port -- the fix command set is the same.

            Students running `show interfaces status` will see Gi1/1 as
            'disabled' rather than 'err-disabled'. The workbook ticket
            calls out 'bpduguard' as the cause (fictional backstory --
            "user plugged a rogue hub in, BPDUs arrived"), so students
            should still reason about why a PC-only port would see BPDUs
            and why bpduguard is the correct long-term defence even
            though this specific simulation uses shutdown.

            Operators who want the real err-disabled state can instead
            wire a second switch trunk into Gi1/1 in the EVE-NG topology
            and re-run setup -- BPDU guard will do the rest.
Fault Type: Access-port outage (simulated BPDU-guard err-disable)

Result:     - SW3 Gi1/1 is 'administratively down' / 'down'.
            - PC2 has no link to its gateway (192.168.20.1).
            - `show errdisable recovery` output is unchanged; the ticket
              narrative still points at bpduguard as the "cause".
            - Fix: `interface Gi1/1 ; shutdown ; no shutdown` (identical
              to the real err-disable recovery procedure).

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-04-capstone-config.unl"
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "interface GigabitEthernet1/1",
    "shutdown",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet1/1"
# Solution markers: access port in VLAN 20 with bpduguard enabled and no shutdown
PREFLIGHT_ACCESS_MARKER = "switchport access vlan 20"
PREFLIGHT_BPDUGUARD_MARKER = "spanning-tree bpduguard enable"
# Fault marker: if the port is already shut, the fault is already injected
PREFLIGHT_FAULT_MARKER = "shutdown"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_ACCESS_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Gi1/1 is not an access port in VLAN 20.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_BPDUGUARD_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Gi1/1 missing '{PREFLIGHT_BPDUGUARD_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    # An explicit 'shutdown' line (not preceded by 'no') indicates fault is present.
    # 'no shutdown' contains 'shutdown' as a substring, so we check for a line that
    # starts with 'shutdown' (after leading whitespace).
    for line in output.splitlines():
        if line.strip() == "shutdown":
            print(f"[!] Pre-flight failed: SW3 Gi1/1 is already shut.")
            print("    Scenario 03 appears to be already injected. Restore with apply_solution.py.")
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
