#!/usr/bin/env python3
"""
Solution Restoration -- Automation Lab 04: API Capstone Config

Restores R1, R2, and R3 to the known-good solution configs under
../../solutions/.  Run this:
  * before injecting a fault (reset to clean state)
  * between tickets (so each scenario starts from a known baseline)
  * after you finish troubleshooting (verify your fix matches the solution)

Console ports must be updated from the EVE-NG web UI before running.
See the CONSOLE_PORTS dict below.

Pass --reset to send 'write erase' and reload before pushing the solution
config.  This guarantees a truly clean slate when stale fault configuration
might otherwise linger after an additive push.

NOTE: We push the FULL solution config -- not just the delta reversal of the
injected fault.  This guarantees the lab is truly in 'known-good' state even
if the student has made exploratory changes beyond the injected fault.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from netmiko import ConnectHandler

# ---------------------------------------------------------------------------
# Environment -- update these values to match your EVE-NG instance
# ---------------------------------------------------------------------------
EVE_NG_HOST = "192.168.x.x"  # EVE-NG server IP -- update to match your environment

# Console telnet ports -- populate from the EVE-NG web UI after starting the lab
CONSOLE_PORTS: dict[str, int | None] = {
    "R1": None,  # update from EVE-NG UI
    "R2": None,  # update from EVE-NG UI
    "R3": None,  # update from EVE-NG UI
}
# ---------------------------------------------------------------------------

SCRIPT_DIR    = Path(__file__).resolve().parent
SOLUTIONS_DIR = SCRIPT_DIR.parent.parent / "solutions"


def _validate_ports(host: str, ports: dict[str, int | None]) -> bool:
    """Return True if all ports are configured, print errors and return False otherwise."""
    missing = [name for name, port in ports.items() if port is None]
    if missing:
        print(
            "[!] Console port(s) not set for: " + ", ".join(missing) + "\n"
            "    Open the EVE-NG web UI, start the lab, and note the telnet ports\n"
            "    assigned to each node.  Then update CONSOLE_PORTS in this script.",
            file=sys.stderr,
        )
        return False
    if host == "192.168.x.x":
        print(
            "[!] EVE_NG_HOST is still the placeholder '192.168.x.x'.\n"
            "    Update EVE_NG_HOST in this script to the real server IP.",
            file=sys.stderr,
        )
        return False
    return True


def parse_config(config_text: str) -> list[str]:
    """Strip comments, blanks, and the 'end' marker -- keep everything else."""
    cmds: list[str] = []
    for line in config_text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("!") or stripped.lower() == "end":
            continue
        cmds.append(stripped)
    return cmds


def erase_device(host: str, name: str, port: int) -> bool:
    """Send 'write erase' and reload, then wait for the device to come back."""
    print(f"\n[*] Erasing {name} ({host}:{port}) ...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        conn.send_command_timing("write erase", read_timeout=30)
        conn.send_command_timing("reload\n", read_timeout=10)
        conn.disconnect()
        print(f"    [*] {name}: reload initiated -- waiting 60 s for device to come back ...")
        time.sleep(60)
        return True
    except Exception as exc:
        print(f"    [!] {name}: erase failed -- {exc}")
        return False


def restore(host: str, name: str, port: int) -> bool:
    """Push full solution config to a device and save."""
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
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=10,
        )
        conn.send_config_set(commands, cmd_verify=False)
        conn.save_config()
        conn.disconnect()
        print(f"    [+] {name} restored.")
        return True
    except Exception as exc:
        print(f"    [!] {name}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore all devices to solution config"
    )
    parser.add_argument("--host", default=EVE_NG_HOST,
                        help="EVE-NG server IP")
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing solution (guaranteed clean slate)")
    args = parser.parse_args()

    host = args.host

    # Merge any --host override with the module-level port dict
    ports = dict(CONSOLE_PORTS)

    if not _validate_ports(host, ports):
        return 2

    print("=" * 60)
    print("Solution Restoration: Removing All Faults")
    print("=" * 60)

    ok = fail = 0

    if args.reset:
        print("\nPhase 1: Resetting devices ...")
        reset_fail = 0
        for name, port in ports.items():
            if not erase_device(host, name, port):  # type: ignore[arg-type]
                reset_fail += 1
        print(f"[=] Phase 1 complete: {len(ports) - reset_fail} reset, {reset_fail} failed.")
        fail += reset_fail
        print("\nPhase 2: Pushing solution configs ...")

    for name, port in ports.items():
        if restore(host, name, port):  # type: ignore[arg-type]
            ok += 1
        else:
            fail += 1

    print("\n" + "=" * 60)
    print(f"Restoration complete: {ok} succeeded, {fail} failed")
    print("=" * 60)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
