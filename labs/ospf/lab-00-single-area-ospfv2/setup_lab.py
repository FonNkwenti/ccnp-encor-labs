#!/usr/bin/env python3
"""
Initial Lab Setup -- OSPF Lab 00 (Single-Area OSPFv2 Fundamentals)

Pushes each router's bare-minimum starting configuration from initial-configs/
via the EVE-NG console. Run once after you build the topology in EVE-NG and
before you begin Section 5 of the workbook.

For troubleshooting scenarios, use scripts/fault-injection/apply_solution.py
instead -- it pushes the full solution config.

Console ports are discovered automatically via the EVE-NG REST API, so the
lab must be STARTED in EVE-NG before running this script. PC1/PC2 load their
.vpc files directly on boot -- no push needed here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ospf/lab-00-single-area-ospfv2.unl"
DEVICES = ["R1", "R2", "R3", "R4", "R5"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push initial configs to EVE-NG lab nodes (console telnet)"
    )
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path on EVE-NG (default: {DEFAULT_LAB_PATH})")
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
        conn.send_config_set(commands)
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

    print("Lab Setup Complete." if fail == 0 else f"Completed with {fail} failure(s).")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
