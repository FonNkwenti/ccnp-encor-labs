"""
Shared EVE-NG automation helpers.

Usage from a lab script (e.g. labs/switching/lab-00-vlans-and-trunking/setup_lab.py):

    import sys
    from pathlib import Path
    # labs/<topic>/<lab>/<script>.py  -> parents[2] = labs/
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common" / "tools"))
    from eve_ng import require_host, discover_ports, connect_node

    host = require_host(args.host)
    ports = discover_ports(host, "ccnp-encor/switching/lab-00-vlans-and-trunking.unl")
    conn = connect_node(host, ports["SW1"])

All helpers fail loudly rather than return defaults — wrong host/port/lab
wastes a lot of telnet timeout, so we catch common configuration errors up
front with clear messages.
"""

from __future__ import annotations

import sys
from typing import Dict, Optional

from netmiko import ConnectHandler

try:
    import requests
except ImportError as exc:  # pragma: no cover - caught at runtime
    raise SystemExit(
        "The 'requests' library is required for EVE-NG REST discovery. "
        "Install with: pip install -r requirements.txt"
    ) from exc


DEFAULT_PLACEHOLDER_HOSTS = {"192.168.x.x", "", None}


class EveNgError(RuntimeError):
    """Raised when EVE-NG automation cannot proceed."""


def require_host(host: Optional[str]) -> str:
    """Return host if it's been overridden from the placeholder; else exit(2).

    Scripts call this immediately after argparse so a forgotten --host fails
    before any slow telnet attempts.
    """
    if host in DEFAULT_PLACEHOLDER_HOSTS:
        print(
            f"[!] --host is not set (got '{host}'). "
            "Pass --host <eve-ng-ip>, e.g. --host 192.168.1.50.",
            file=sys.stderr,
        )
        sys.exit(2)
    return host


def discover_ports(
    host: str,
    lab_path: str,
    username: str = "admin",
    password: str = "eve",
    scheme: str = "http",
    timeout: float = 5.0,
) -> Dict[str, int]:
    """Return {node_name: console_telnet_port} for all nodes in a lab.

    Args:
        host: EVE-NG server IP/hostname (no scheme).
        lab_path: path of the .unl file on the EVE-NG server, e.g.
            "ccnp-encor/switching/lab-00-vlans-and-trunking.unl". EVE-NG's API
            expects this relative to /opt/unetlab/labs/.
        username/password: EVE-NG web UI credentials (default admin/eve).
        scheme: "http" (default) or "https".
        timeout: per-request timeout in seconds.

    Raises:
        EveNgError if auth fails, the lab isn't found, or no nodes have
        console URLs (lab not started).
    """
    base = f"{scheme}://{host}"
    # EVE-NG expects a leading slash on the lab path in the URL
    lab_url_path = lab_path if lab_path.startswith("/") else "/" + lab_path

    session = requests.Session()
    try:
        login = session.post(
            f"{base}/api/auth/login",
            json={"username": username, "password": password, "html5": "-1"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise EveNgError(
            f"Could not reach EVE-NG at {base}: {exc}"
        ) from exc

    if login.status_code != 200:
        raise EveNgError(
            f"EVE-NG auth failed ({login.status_code}): {login.text.strip()}"
        )

    nodes_resp = session.get(
        f"{base}/api/labs{lab_url_path}/nodes", timeout=timeout
    )
    if nodes_resp.status_code != 200:
        raise EveNgError(
            f"Could not fetch nodes for lab '{lab_path}' "
            f"({nodes_resp.status_code}): {nodes_resp.text.strip()}"
        )

    data = nodes_resp.json().get("data", {})
    ports: Dict[str, int] = {}
    for node in data.values():
        name = node.get("name")
        url = node.get("url")
        # url looks like "telnet://<host>:<port>"; missing when node is stopped
        if name and url and ":" in url:
            try:
                ports[name] = int(url.rsplit(":", 1)[-1])
            except ValueError:
                continue

    if not ports:
        raise EveNgError(
            f"No console ports discovered for '{lab_path}'. "
            "Make sure the lab is started in EVE-NG (Actions -> Start all nodes)."
        )
    return ports


def connect_node(host: str, port: int, timeout: int = 10):
    """Open a Netmiko telnet session to an EVE-NG console port.

    Credentials are blank by default — matches the unconfigured IOSv/IOSvL2
    console on EVE-NG. Escalates to privileged EXEC automatically so that
    send_config_set() works regardless of whether the node booted to '>' or '#'.
    """
    conn = ConnectHandler(
        device_type="cisco_ios_telnet",
        host=host,
        port=port,
        username="",
        password="",
        secret="",
        timeout=timeout,
        global_delay_factor=2,
    )
    # Normalize to privileged EXEC regardless of where the console was left:
    #   (config)# → exit → # (already enabled, skip enable())
    #   >         → enable → #
    #   #         → already there, nothing to do
    prompt = conn.find_prompt()
    if "(config" in prompt:
        conn.exit_config_mode()
    elif not conn.check_enable_mode():
        conn.enable()
    conn.clear_buffer()  # flush syslog messages before caller uses the session
    return conn


def erase_device_config(host: str, name: str, port: int) -> bool:
    """Send 'write erase' to clear a device's startup-config.

    Handles the IOS [confirm] prompt automatically. Returns True on
    success, False on any connection or command failure.
    """
    print(f"[*] {name}: erasing config...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: connection failed -- {exc}")
        return False
    try:
        conn.send_command("write erase", expect_string=r"\[confirm\]")
        conn.send_command("\n", expect_string=r"#")
        print(f"[+] {name}: config erased.")
        return True
    except Exception as exc:
        print(f"[!] {name}: reset failed -- {exc}")
        return False
    finally:
        conn.disconnect()
