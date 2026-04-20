#!/usr/bin/env python3
"""
Solution: Task 4 — Retrieve Interface Configuration via NETCONF get-config.

Connects to R1 on port 830, sends a get-config RPC with an ietf-interfaces
subtree filter, and prints each interface name and IPv4 address found in the
running datastore.
"""

from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
import xml.etree.ElementTree as ET

ROUTER_IP = "10.1.12.1"   # R1 Gi1 address — reachable from workstation via management
NETCONF_PORT = 830
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

IETF_INTERFACES_NS = "urn:ietf:params:xml:ns:yang:ietf-interfaces"
IETF_IP_NS = "urn:ietf:params:xml:ns:yang:ietf-ip"

FILTER = """
<filter type="subtree">
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
</filter>
"""


def get_interfaces():
    print(f"[*] Connecting to {ROUTER_IP}:{NETCONF_PORT} via NETCONF...")
    try:
        with manager.connect(
            host=ROUTER_IP,
            port=NETCONF_PORT,
            username=USERNAME,
            password=PASSWORD,
            hostkey_verify=False,
            device_params={"name": "csr"},
            timeout=30,
        ) as m:
            print("[+] Connected. Sending get-config RPC (source=running)...")
            reply = m.get_config(source="running", filter=FILTER)

            root = ET.fromstring(reply.xml)
            ns = {"if": IETF_INTERFACES_NS, "ip": IETF_IP_NS}

            interfaces = root.findall(".//if:interface", ns)
            print(f"\n{'Interface':<25} {'IPv4 Address':<20} {'Admin Status'}")
            print("-" * 60)
            for iface in interfaces:
                name = iface.findtext("if:name", default="N/A", namespaces=ns)
                enabled = iface.findtext("if:enabled", default="true", namespaces=ns)
                status = "up" if enabled.lower() == "true" else "down"

                addr_el = iface.find(".//ip:address/ip:ip", ns)
                ipv4 = addr_el.text if addr_el is not None else "—"
                print(f"{name:<25} {ipv4:<20} {status}")

    except AuthenticationError:
        print("[!] Authentication failed — check username/password")
    except SSHError as e:
        print(f"[!] SSH/NETCONF connection error: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")


if __name__ == "__main__":
    get_interfaces()
