#!/usr/bin/env python3
"""
Lab Setup: Network Assurance Lab 05 — Comprehensive Troubleshooting (Capstone II)

Pushes each node's pre-broken initial configuration from initial-configs/ via the
EVE-NG console. Run once after you build the topology in EVE-NG to load the
pre-broken state before beginning Section 5 of the workbook.

Capstone II is a pre-broken lab: initial configs contain the full Network Assurance
monitoring stack with five concurrent faults pre-injected across R1, R3, and SW1.
The student diagnoses and fixes all five per workbook.md Section 5.

PC1 and PC2 are VPCS nodes — configure them manually from their EVE-NG console:
  PC1: ip 192.168.10.10 255.255.255.0 192.168.10.1
  PC2: ip 192.168.20.10 255.255.255.0 192.168.20.1

Console ports are discovered automatically via the EVE-NG REST API, so the
lab must be STARTED in EVE-NG before running this script.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>
    python3 setup_lab.py --host <eve-ng-ip> --reset   # erase before push
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# labs/network-assurance/lab-05-capstone-troubleshoot/setup_lab.py
# parents[2] == labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ccnp-encor/network-assurance/lab-05-capstone-troubleshoot.unl"
DEVICES = ["R1", "R2", "R3", "SW1", "SW2"]  # VPCS nodes (PC1, PC2) configured manually


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push pre-broken initial configs for network-assurance lab-05 (Capstone II)"
    )
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path on EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing initial configs")
    return parser.parse_args()


def push_config(host: str, port: int, config_file: Path) -> bool:
    print(f"  Connecting to {host}:{port} ...")
    if not config_file.exists():
        print(f"  [!] Config file not found: {config_file}")
        return False

    commands = [
        line.strip() for line in config_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("!") and line.strip().lower() != "end"
    ]
    try:
        conn = connect_node(host, port)
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"  [+] Loaded {config_file.name}")
        return True
    except Exception as exc:
        print(f"  [!] Failed on {config_file.name}: {exc}")
        return False


def main() -> int:
    args = parse_args()
    host = require_host(args.host)

    print("=" * 60)
    print("Lab Setup: Network Assurance Lab 05 — Capstone II (pre-broken)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    print(f"[+] Discovered {len(ports)} node(s) in {args.lab_path}")
    fail = 0

    if args.reset:
        print("\nPhase 1: Resetting devices...")
        reset_fail = 0
        for name in DEVICES:
            port = ports.get(name)
            if port is None:
                print(f"[!] {name}: not found in lab {args.lab_path} -- skipping reset")
                reset_fail += 1
                continue
            if not erase_device_config(host, name, port):
                reset_fail += 1
        print(f"[=] Phase 1 complete: {len(DEVICES) - reset_fail} reset, {reset_fail} failed.")
        fail += reset_fail
        print("\nPhase 2: Pushing pre-broken initial configs...")

    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"--- Skipping {name}: not found in lab ---")
            fail += 1
            continue
        print(f"--- Setting up {name} ---")
        cfg = SCRIPT_DIR / "initial-configs" / f"{name}.cfg"
        if not push_config(host, port, cfg):
            fail += 1

    print()
    if fail == 0:
        print("[+] All devices loaded with pre-broken state.")
        print("[+] Five concurrent faults are active — work Section 5 of workbook.md.")
        print("[+] NOTE: PC1 and PC2 are VPCS nodes — configure them manually.")
        print("      PC1: ip 192.168.10.10 255.255.255.0 192.168.10.1")
        print("      PC2: ip 192.168.20.10 255.255.255.0 192.168.20.1")
    else:
        print(f"[!] Completed with {fail} failure(s). Check logs above.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
