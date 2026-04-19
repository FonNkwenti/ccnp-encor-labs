#!/usr/bin/env python3
"""
Lab Setup: EIGRP Lab 04 -- Comprehensive Troubleshooting (Capstone II)

Pushes initial-configs/<node>.cfg to each router via its EVE-NG console
port. Console ports are discovered dynamically from the EVE-NG REST API;
no hardcoded port numbers.

initial-configs carry the full Lab 03 capstone dual-stack EIGRP build
with FIVE concurrent faults pre-injected:

  * R1: non-default K-values under IPv4 AF   (metric weights 0 2 0 1 0 0)
  * R3: passive-interface on transit Gi0/1 IPv4 AF
  * R2: missing IPv4 network statement for 10.24.0.0/30
  * R4: IPv4 AF stub set to receive-only (instead of connected)
  * R2: variance 8 missing from both AFs

Students boot this state and diagnose symptoms from Section 9 of
workbook.md. Restore with scripts/fault-injection/apply_solution.py.

PC1 and PC2 read their .vpc files directly from EVE-NG on boot -- no push here.

Usage:
    python3 setup_lab.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402


DEFAULT_LAB_PATH = "eigrp/lab-04-capstone-troubleshoot.unl"
DEVICES = ["R1", "R2", "R3", "R4"]
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
    parser = argparse.ArgumentParser(description="Push pre-broken configs for EIGRP lab-04")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing initial configs")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Lab Setup: EIGRP Lab 04 -- Comprehensive Troubleshooting")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0

    if args.reset:
        print("\nPhase 1: Resetting devices...")
        for name in DEVICES:
            port = ports.get(name)
            if port is None:
                print(f"[!] {name}: not found in lab {args.lab_path} — skipping reset")
                fail += 1
                continue
            if not erase_device_config(host, name, port):
                fail += 1
        print(f"\nPhase 2: Pushing initial configs...")

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
    print("[+] All devices configured. PC1 and PC2 load their .vpc files on boot.")
    print("[+] Lab is now in the BROKEN baseline state -- begin troubleshooting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
