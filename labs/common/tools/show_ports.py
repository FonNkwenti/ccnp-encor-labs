#!/usr/bin/env python3
"""Print the console telnet port for each node in an EVE-NG lab.

Smoke test for the REST API -- confirms the lab is started and wired before
you run setup_lab.py / apply_solution.py. Copy a `telnet <host> <port>` line
into a terminal to verify console reachability per node.

Usage:
    python labs/common/tools/show_ports.py --lab-path switching/lab-00-vlans-and-trunking.unl
    python labs/common/tools/show_ports.py --host 192.168.1.214 --lab-path switching/lab-00-vlans-and-trunking.unl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from eve_ng import EveNgError, discover_ports  # noqa: E402


DEFAULT_HOST = "192.168.1.214"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"EVE-NG server IP (default: {DEFAULT_HOST})")
    parser.add_argument("--lab-path", required=True,
                        help="Lab .unl path on EVE-NG, e.g. "
                             "switching/lab-00-vlans-and-trunking.unl")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="eve")
    args = parser.parse_args()

    try:
        ports = discover_ports(
            host=args.host,
            lab_path=args.lab_path,
            username=args.username,
            password=args.password,
        )
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1

    name_width = max(len(n) for n in ports) if ports else 4
    print(f"{'Node'.ljust(name_width)}  Port   Telnet command")
    print(f"{'-' * name_width}  -----  {'-' * 30}")
    for name in sorted(ports):
        port = ports[name]
        print(f"{name.ljust(name_width)}  {port}  telnet {args.host} {port}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
