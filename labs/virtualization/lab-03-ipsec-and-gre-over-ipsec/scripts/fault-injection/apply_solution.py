#!/usr/bin/env python3
"""
Solution Restoration -- Virtualization Lab 03

Restores all devices to the known-good solution configs under ../../solutions/.
Run this:
  * before injecting a fault (reset to clean state)
  * between tickets (so each scenario starts from a known baseline)
  * after you finish troubleshooting (verify your fix matches the solution)

Console ports are discovered via the EVE-NG REST API, so the lab must be
STARTED in EVE-NG before running.

NOTE: We push the FULL solution config -- not just the delta reversal of the
injected fault. This guarantees the lab is truly in "known-good" state even
if the student has made exploratory changes beyond the injected fault.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

SOLUTIONS_DIR = SCRIPT_DIR.parent.parent / "solutions"
DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-03-ipsec-and-gre-over-ipsec.unl"
DEVICES = ["R1", "R2", "R3", "R4"]


def parse_config(config_text: str) -> list[str]:
    """Strip comments, blanks, and the 'end' marker -- keep everything else."""
    cmds = []
    for line in config_text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("!") or stripped.lower() == "end":
            continue
        cmds.append(stripped)
    return cmds


def restore(host: str, name: str, port: int) -> bool:
    cfg = SOLUTIONS_DIR / f"{name}.cfg"
    print(f"\n[*] Restoring {name} ({host}:{port}) from {cfg.name}")
    if not cfg.exists():
        print(f"    [!] Solution config not found: {cfg}")
        return False

    commands = parse_config(cfg.read_text(encoding="utf-8"))
    if not commands:
        print(f"    [!] No commands parsed from {cfg}")
        return False

    try:
        conn = connect_node(host, port)
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"    [+] {name} restored.")
        return True
    except Exception as exc:
        print(f"    [!] {name}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore all devices to solution config")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path on EVE-NG (default: {DEFAULT_LAB_PATH})")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    ok = fail = 0
    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"\n[!] {name} not found in lab -- skipping.")
            fail += 1
            continue
        if restore(host, name, port):
            ok += 1
        else:
            fail += 1

    print("\n" + "=" * 60)
    print(f"Restoration Complete: {ok} succeeded, {fail} failed")
    print("=" * 60)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
