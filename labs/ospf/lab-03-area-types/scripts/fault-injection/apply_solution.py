#!/usr/bin/env python3
"""
Solution Restoration: OSPF Lab 03 -- Area Types: Stub, Totally Stubby, and NSSA

Pushes the full solution configs from ../../solutions/ to all six routers,
overwriting any injected faults and restoring the lab to the known-good
multi-area OSPFv2 + OSPFv3 state with Totally Stubby Area 1, NSSA Area 2,
and R6 as a new internal Area 1 router.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ospf/lab-03-area-types.unl"
DEVICES = ["R1", "R2", "R3", "R4", "R5", "R6"]
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"


def load_commands(cfg_path: Path) -> list[str]:
    lines: list[str] = []
    for raw in cfg_path.read_text().splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("!") or stripped == "end":
            continue
        lines.append(raw)
    return lines


def restore(host: str, name: str, port: int) -> bool:
    cfg_path = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_path.exists():
        print(f"[!] {name}: solution file not found at {cfg_path}")
        return False

    print(f"\n[*] {name}: restoring via {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: connection failed -- {exc}")
        return False

    try:
        conn.send_config_set(load_commands(cfg_path))
        conn.save_config()
        print(f"[+] {name}: solution applied.")
        return True
    except Exception as exc:
        print(f"[!] {name}: restore failed -- {exc}")
        return False
    finally:
        conn.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore OSPF lab-03 to solution state")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing solution (guaranteed clean slate)")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Solution Restoration: OSPF Lab 03 -- Area Types")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0

    if args.reset:
        print("\nPhase 1: Resetting devices...")
        reset_fail = 0
        for name in DEVICES:
            port = ports.get(name)
            if port is None:
                print(f"[!] {name}: not found in lab {args.lab_path} — skipping reset")
                reset_fail += 1
                continue
            if not erase_device_config(host, name, port):
                reset_fail += 1
        print(f"[=] Phase 1 complete: {len(DEVICES) - reset_fail} reset, {reset_fail} failed.")
        fail += reset_fail
        print(f"\nPhase 2: Pushing solution configs...")

    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name}: not found in lab {args.lab_path}")
            fail += 1
            continue
        if not restore(host, name, port):
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed. Lab not fully restored.")
        return 1
    print("[+] All devices restored to solution state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
