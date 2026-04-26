#!/usr/bin/env python3
"""
Inject All Faults: Multicast Lab 03 -- Capstone I

Runs inject_scenario_01, _02, _03 in sequence to inject all three faults
simultaneously. Useful for practicing multi-fault triage.

Usage:
    python3 inject_all.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIOS = [
    "inject_scenario_01.py",
    "inject_scenario_02.py",
    "inject_scenario_03.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject all faults for Multicast lab-03")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path",
                        default="multicast/lab-03-capstone-config.unl")
    args = parser.parse_args()

    print("=" * 60)
    print("Injecting ALL faults for Multicast Lab 03 (Capstone I)")
    print("=" * 60)

    fail = 0
    for script in SCENARIOS:
        print(f"\n>>> Running {script} ...")
        rc = subprocess.call(
            [sys.executable, str(SCRIPT_DIR / script),
             "--host", args.host, "--lab-path", args.lab_path],
        )
        if rc != 0:
            print(f"[!] {script} exited with rc={rc}")
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} scenario(s) failed to inject.")
        return 1
    print("[+] All three faults injected. See workbook.md Section 9 for Tickets 1-3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
