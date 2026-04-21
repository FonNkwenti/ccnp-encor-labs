#!/usr/bin/env python3
"""
Restore vSmart and vEdge2 to the known-good solution state.

Reads solutions/vSmart.cfg and solutions/vEdge2.cfg from the lab root,
pushes each line by line (skipping blanks and comment lines beginning
with "!"), then commits.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netmiko import ConnectHandler

DEFAULT_EVE_NG_HOST = "192.168.x.x"

# Telnet ports assigned in EVE-NG UI -- update both before use
VSMART_PORT = 0
VEDGE2_PORT = 0

SOLUTIONS_DIR = Path(__file__).resolve().parents[2] / "solutions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore vSmart and vEdge2 to the known-good solution state"
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_EVE_NG_HOST,
        help="EVE-NG server IP (default: %(default)s)",
    )
    return parser.parse_args()


def load_cfg(filename: str) -> list[str]:
    """Read a solution config file, skipping blanks and comment lines."""
    cfg_path = SOLUTIONS_DIR / filename
    if not cfg_path.exists():
        print(f"[!] Solution file not found: {cfg_path}", file=sys.stderr)
        sys.exit(2)
    lines = []
    for raw in cfg_path.read_text().splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("!"):
            continue
        lines.append(line)
    return lines


def push_config(eve_ng_host: str, device_name: str, port: int, commands: list[str]) -> int:
    """Connect to a device via telnet, push commands, and commit."""
    device = {
        "device_type": "cisco_ios_telnet",
        "host": eve_ng_host,
        "port": port,
        "username": "admin",
        "password": "admin",
        "config_mode_command": "config",
        "cmd_verify": False,
        "exit_config_mode": False,
    }

    print(f"[*] Connecting to {device_name} on {eve_ng_host}:{port} ...")
    try:
        conn = ConnectHandler(**device)
    except Exception as exc:
        print(f"[!] Connection to {device_name} failed: {exc}", file=sys.stderr)
        return 3

    try:
        print(f"[*] Pushing solution config to {device_name} ({len(commands)} lines) ...")
        conn.send_config_set(commands)
        conn.send_command("commit")
        print(f"[+] {device_name} restored to known-good state.")
    finally:
        conn.disconnect()

    return 0


def main() -> int:
    args = parse_args()

    print("=" * 60)
    print("Apply Solution: vSmart + vEdge2")
    print("=" * 60)

    vsmart_cfg = load_cfg("vSmart.cfg")
    vedge2_cfg = load_cfg("vEdge2.cfg")

    rc = push_config(args.host, "vSmart", VSMART_PORT, vsmart_cfg)
    if rc != 0:
        return rc

    rc = push_config(args.host, "vEdge2", VEDGE2_PORT, vedge2_cfg)
    if rc != 0:
        return rc

    print("=" * 60)
    print("[+] All devices restored. Lab is in the known-good solution state.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
