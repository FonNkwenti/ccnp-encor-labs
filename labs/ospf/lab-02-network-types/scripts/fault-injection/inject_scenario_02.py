#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Wrong OSPF Priority on R3 Gi0/0

Target:     R3 (interface Gi0/0 -- the Area 0 broadcast segment)
Injects:    Overrides `ip ospf priority 0` with `ip ospf priority 255`
            on R3 Gi0/0. No process clear is issued -- the current
            election stands until something forces a re-election.
Fault Type: DR/BDR Election Misconfiguration

Result:     Within ~10 seconds, R1 and R2 see R3 advertise Priority 255
            in its Hellos (visible in `show ip ospf neighbor`). R3 stays
            DROTHER for now (OSPF does not pre-empt the existing DR), so
            the fault is latent -- but the next time R1 goes through
            WAITING (reload, process clear, or interface flap) R3 will
            win DR on priority tie-break (RID 3.3.3.3 > RID 1.1.1.1).

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


DEFAULT_LAB_PATH = "ospf/lab-02-network-types.unl"
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "ip ospf priority 255",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Solution marker: R3 Gi0/0 explicitly set to priority 0
PREFLIGHT_SOLUTION_MARKER = "ip ospf priority 0"
# Fault marker: priority 255 already present -> fault already injected
PREFLIGHT_FAULT_MARKER = "ip ospf priority 255"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R3 Gi0/0 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears to be already injected.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R3 priority 255 on Area 0)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (Wrong OSPF Priority on R3 Gi0/0)")
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
