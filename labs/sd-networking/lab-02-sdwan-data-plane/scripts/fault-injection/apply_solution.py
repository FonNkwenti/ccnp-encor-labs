#!/usr/bin/env python3
"""
Solution Restoration: SD-WAN Lab 02 — Data Plane and Application Policies

Restores vSmart and vEdge2 to their known-good solution state by pushing the
contents of ../../solutions/{Device}.cfg to each device.

Only vSmart (Tickets 1 and 2) and vEdge2 (Ticket 3) are affected by the three
fault scenarios; vManage, vBond, vEdge1, and R-TRANSPORT are not touched.

IMPORTANT — Viptela OS limitation:
    The --reset flag is present for CLI consistency with other lab scripts but
    it is a no-op for Viptela OS devices. Viptela has no 'write erase' equivalent
    that is safe to run non-interactively. Instead, each solution config is pushed
    additively and the commit overwrites any injected fault values. This is
    sufficient to restore lab state after any of the three fault scenarios.

Usage:
    python3 apply_solution.py --host <eve-ng-ip>
    python3 apply_solution.py --host <eve-ng-ip> --reset   # --reset is accepted but no-op
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netmiko import ConnectHandler

SCRIPT_DIR = Path(__file__).resolve().parent
SOLUTIONS_DIR = SCRIPT_DIR.parents[1] / "solutions"

# Devices affected by fault scenarios — Viptela OS only
# Tickets 1 & 2: vSmart | Ticket 3: vEdge2
VIPTELA_DEVICES = ["vSmart", "vEdge2"]

# Viptela OS credentials (EVE-NG image defaults)
VIPTELA_USERNAME = "admin"
VIPTELA_PASSWORD = "admin"


def load_solution_commands(cfg_path: Path) -> list[str]:
    """Read a solution .cfg file and return non-empty, non-comment lines.

    Strips lines starting with '!' and blank lines. A trailing 'commit'
    is appended to ensure changes take effect on Viptela OS.
    """
    lines: list[str] = []
    for raw in cfg_path.read_text().splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("!") or stripped == "end":
            continue
        lines.append(stripped)
    # Viptela requires an explicit commit — solution files do not include one
    if lines and lines[-1] != "commit":
        lines.append("commit")
    return lines


def restore_viptela(host: str, name: str, port: int) -> bool:
    """Push solution config to a Viptela OS device via EVE-NG console telnet.

    Returns True on success, False on any connection or command error.
    """
    cfg_path = SOLUTIONS_DIR / f"{name}.cfg"
    if not cfg_path.exists():
        print(f"[!] {name}: solution file not found at {cfg_path}")
        return False

    commands = load_solution_commands(cfg_path)
    if not commands:
        print(f"[!] {name}: solution file is empty or has no actionable lines")
        return False

    print(f"\n[*] {name}: restoring via {host}:{port} ...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username=VIPTELA_USERNAME,
            password=VIPTELA_PASSWORD,
            secret="",
            timeout=15,
        )
    except Exception as exc:
        print(f"[!] {name}: connection failed -- {exc}")
        return False

    try:
        conn.send_config_set(
            commands,
            config_mode_command="config",
            cmd_verify=False,
            exit_config_mode=False,
        )
        print(f"[+] {name}: solution applied.")
        return True
    except Exception as exc:
        print(f"[!] {name}: restore failed -- {exc}")
        return False
    finally:
        conn.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore SD-WAN lab-02 affected devices to solution state"
    )
    parser.add_argument(
        "--host",
        default="192.168.x.x",
        help="EVE-NG server IP (required)",
    )
    parser.add_argument(
        "--vSmart-port",
        type=int,
        default=0,
        dest="vsmart_port",
        help="Console port for vSmart (from EVE-NG web UI, default: 0)",
    )
    parser.add_argument(
        "--vEdge2-port",
        type=int,
        default=0,
        dest="vedge2_port",
        help="Console port for vEdge2 (from EVE-NG web UI, default: 0)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Accepted for CLI consistency; no-op for Viptela OS devices "
            "(no 'write erase' equivalent available non-interactively)"
        ),
    )
    args = parser.parse_args()

    if args.host in {"192.168.x.x", "", None}:
        print("[!] --host is not set. Pass --host <eve-ng-ip>.", file=sys.stderr)
        return 2

    print("=" * 60)
    print("Solution Restoration: SD-WAN Lab 02 — Data Plane and Policies")
    print("=" * 60)

    if args.reset:
        print(
            "[!] --reset flag noted. Viptela OS does not support automated config erase.\n"
            "    Pushing solution configs additively — fault values will be overwritten.\n"
        )

    device_ports = {
        "vSmart": args.vsmart_port,
        "vEdge2": args.vedge2_port,
    }

    fail = 0
    for name in VIPTELA_DEVICES:
        port = device_ports[name]
        if port == 0:
            print(
                f"\n[!] {name}: console port is 0 (placeholder). "
                f"Pass --{name.lower()}-port <port> to restore this device."
            )
            fail += 1
            continue
        if not restore_viptela(args.host, name, port):
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed or were skipped. Lab not fully restored.")
        return 1
    print("[+] All affected devices restored to known-good state.")
    print("[*] vSmart: app-route-policy and vpn-list VPN1 restored.")
    print("[*] vEdge2: VPN 0 default route restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
