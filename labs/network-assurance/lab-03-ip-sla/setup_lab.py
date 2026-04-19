#!/usr/bin/env python3
"""
Initial Lab Setup -- Network Assurance Lab 03 (IP SLA Probes and Tracking)

Pushes each node's starting configuration from initial-configs/ via the
EVE-NG console. Run once after you build the topology in EVE-NG and before
you begin Section 4 of the workbook.

PC1 and PC2 are VPCS nodes -- configure them manually from their EVE-NG console:
  PC1: ip 192.168.10.10 255.255.255.0 192.168.10.1
  PC2: ip 192.168.20.10 255.255.255.0 192.168.20.1

Console ports are discovered automatically via the EVE-NG REST API, so the
lab must be STARTED in EVE-NG before running this script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# labs/network-assurance/lab-03-ip-sla/setup_lab.py
# parents[2] == labs/
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ccnp-encor/network-assurance/lab-03-ip-sla.unl"
DEVICES = ["R1", "R2", "R3", "SW1", "SW2"]  # VPCS nodes (PC1, PC2) configured manually


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push initial configs to EVE-NG lab nodes (console telnet)"
    )
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path on EVE-NG (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing initial configs")
    return parser.parse_args()


def push_config(host: str, port: int, config_file: Path) -> bool:
    print(f"Connecting to {host}:{port} ...")
    if not config_file.exists():
        print(f"  [!] Config file not found: {config_file}")
        return False

    commands = [
        line.strip() for line in config_file.read_text().splitlines()
        if line.strip() and not line.startswith("!")
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
        print("\nPhase 2: Pushing initial configs...")

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
        print("Lab Setup Complete.")
        print("NOTE: PC1 and PC2 are VPCS nodes -- configure them manually.")
        print("  PC1: ip 192.168.10.10 255.255.255.0 192.168.10.1")
        print("  PC2: ip 192.168.20.10 255.255.255.0 192.168.20.1")
    else:
        print(f"Completed with {fail} failure(s).")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
