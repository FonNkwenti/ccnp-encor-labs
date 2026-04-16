#!/usr/bin/env python3
"""
Lab Setup: OSPF Lab 02 -- Network Types + DR/BDR Manipulation

Pushes initial-configs/<node>.cfg to each router via its EVE-NG console
port. Console ports are discovered dynamically from the EVE-NG REST API;
no hardcoded port numbers.

The initial-configs here are the lab-01 solution state (full multi-area
OSPFv2 + OSPFv3 dual-stack). The student then tunes OSPF priorities on
the Area 0 broadcast segment and converts the Area 1 / Area 2 transit
links to OSPF network type point-to-point.

PC1/PC2 read their .vpc files directly from EVE-NG on boot -- no push
needed here.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ospf/lab-02-network-types.unl"
DEVICES = ["R1", "R2", "R3", "R4", "R5"]
CONFIG_DIR = SCRIPT_DIR / "initial-configs"


def load_commands(cfg_path: Path) -> list[str]:
    """Read a .cfg file, skipping blanks, comments, and the trailing 'end'."""
    lines: list[str] = []
    for raw in cfg_path.read_text().splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("!") or stripped == "end":
            continue
        lines.append(raw)
    return lines


def push_device(host: str, name: str, port: int) -> bool:
    cfg_path = CONFIG_DIR / f"{name}.cfg"
    if not cfg_path.exists():
        print(f"[!] {name}: config file not found at {cfg_path}")
        return False

    print(f"\n[*] {name}: connecting to {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: connection failed -- {exc}")
        return False

    try:
        commands = load_commands(cfg_path)
        conn.send_config_set(commands)
        conn.save_config()
        print(f"[+] {name}: config applied.")
        return True
    except Exception as exc:
        print(f"[!] {name}: push failed -- {exc}")
        return False
    finally:
        conn.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Push initial configs for OSPF lab-02")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Lab Setup: OSPF Lab 02 -- Network Types + DR/BDR Manipulation")
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
        if not push_device(host, name, port):
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed. Check logs above.")
        return 1
    print("[+] All devices configured. PC1/PC2 load their .vpc files on boot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
