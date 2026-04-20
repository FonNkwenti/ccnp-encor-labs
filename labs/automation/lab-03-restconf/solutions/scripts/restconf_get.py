#!/usr/bin/env python3
"""
RESTCONF GET — Retrieve interface list from R1 via ietf-interfaces model.

Task 2 solution: sends GET to /restconf/data/ietf-interfaces:interfaces
and prints a formatted table of interface names, IPv4 addresses, and
admin status.
"""

import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP = "10.1.12.1"
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

BASE_URL = f"https://{ROUTER_IP}/restconf/data"
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

def get_interfaces():
    url = f"{BASE_URL}/ietf-interfaces:interfaces"
    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        verify=False,
        timeout=10,
    )
    print(f"Status: {response.status_code}")
    response.raise_for_status()
    return response.json()

def print_interface_table(data):
    interfaces = data.get("ietf-interfaces:interfaces", {}).get("interface", [])
    print(f"\n{'Name':<25} {'Type':<30} {'Enabled':<10} {'IPv4 Address'}")
    print("-" * 80)
    for iface in interfaces:
        name = iface.get("name", "")
        iface_type = iface.get("type", "").replace("iana-if-type:", "")
        enabled = iface.get("enabled", True)
        ipv4_block = iface.get("ietf-ip:ipv4", {})
        addresses = ipv4_block.get("address", [])
        ipv4 = f"{addresses[0]['ip']}/{addresses[0]['prefix-length']}" if addresses else "—"
        print(f"{name:<25} {iface_type:<30} {str(enabled):<10} {ipv4}")

if __name__ == "__main__":
    print("=" * 50)
    print("RESTCONF GET: ietf-interfaces:interfaces")
    print("=" * 50)
    data = get_interfaces()
    print_interface_table(data)
