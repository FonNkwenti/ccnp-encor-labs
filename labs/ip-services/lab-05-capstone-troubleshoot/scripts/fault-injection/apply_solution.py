#!/usr/bin/env python3
"""
Solution Restoration: IP Services Lab 05 -- Comprehensive Troubleshooting Capstone II

Pushes the full solution configs from ../../solutions/ to R1, R2, R3,
returning the lab to the known-good end-state with all 6 faults resolved.

Use this to:
  - Verify your fixes by comparing against the reference
  - Reset between troubleshooting attempts

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

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICES = ["R1", "R2", "R3"]
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
    parser = argparse.ArgumentParser(description="Restore IP Services lab-05 to solution state")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing solution (guaranteed clean slate)")
    args = parser.parse_args()
    host = require_host(args.host)
    print("=" * 60)
    print("Solution Restoration: IP Services Lab 05 (Capstone II)")
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
