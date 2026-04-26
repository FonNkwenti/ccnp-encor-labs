from netmiko import ConnectHandler
import argparse
import os
from pathlib import Path

DEFAULT_EVE_NG_HOST = "192.168.x.x"

SOLUTIONS_DIR = Path(__file__).resolve().parents[2] / "solutions"

VIPTELA_DEVICES = [
    {"name": "vManage", "file": "vManage.cfg", "port": 0},
    {"name": "vSmart",  "file": "vSmart.cfg",  "port": 0},
    {"name": "vBond",   "file": "vBond.cfg",   "port": 0},
    {"name": "vEdge1",  "file": "vEdge1.cfg",  "port": 0},
    {"name": "vEdge2",  "file": "vEdge2.cfg",  "port": 0},
]


def parse_args():
    parser = argparse.ArgumentParser(description="Restore all SD-WAN devices to known-good solution state")
    parser.add_argument("--host", default=DEFAULT_EVE_NG_HOST,
                        help="EVE-NG server IP (default: %(default)s)")
    return parser.parse_args()


def push_viptela_config(name, port, config_file, eve_ng_host):
    print(f"Restoring {name} ({eve_ng_host}:{port})...")
    try:
        if not os.path.exists(config_file):
            print(f"  Error: {config_file} not found.")
            return False

        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=eve_ng_host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=20,
            global_cmd_verify=False,
            config_mode_command="config",
        )

        with open(config_file, 'r') as f:
            commands = [line.rstrip() for line in f if line.strip() and not line.startswith('!')]

        conn.send_config_set(commands, cmd_verify=False, exit_config_mode=False)
        conn.send_command("commit")
        print(f"  Restored from {config_file}")
        conn.disconnect()
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False


def run(eve_ng_host):
    print(f"Restoring lab-05 to known-good state (EVE-NG: {eve_ng_host})")
    print()
    print("NOTE: Update port numbers in VIPTELA_DEVICES before running.")
    print()

    for device in VIPTELA_DEVICES:
        cfg_path = SOLUTIONS_DIR / device["file"]
        push_viptela_config(device["name"], device["port"], cfg_path, eve_ng_host)

    print()
    print("Restore complete.")
    print("Run 'show control connections' on vEdge1 and vEdge2 to confirm fabric health.")


if __name__ == "__main__":
    args = parse_args()
    run(args.host)
