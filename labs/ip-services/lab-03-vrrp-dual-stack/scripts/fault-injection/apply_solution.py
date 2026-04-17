#!/usr/bin/env python3
"""
Solution Restoration: IP Services Lab 03 -- VRRP and Dual-Stack

Pushes the full solution configs from ../../solutions/ to R1, R2, R3,
returning the lab to the known-good end-state with VRRPv3 group 1 IPv4
and IPv6 address-families, interface tracking, and dual-stack OSPFv3.

Use this to:
  - Reset after a fault-injection scenario
  - Compare your build against the reference

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-03-vrrp-dual-stack.unl"
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
    parser = argparse.ArgumentParser(description="Restore IP Services lab-03 to solution state")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Solution Restoration: IP Services Lab 03 (VRRPv3 Dual-Stack)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0
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
