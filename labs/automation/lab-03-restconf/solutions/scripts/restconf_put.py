#!/usr/bin/env python3
"""
RESTCONF PUT — Create Loopback30 on R1 with dual-stack (IPv4 + IPv6).

Task 3 solution: sends PUT to /restconf/data/ietf-interfaces:interfaces/interface=Loopback30
with a JSON payload containing both IPv4 (10.30.30.1/32) and IPv6 (2001:db8:30::1/128).

HTTP 201 Created = new resource; HTTP 204 No Content = existing resource replaced.
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

PAYLOAD = {
    "ietf-interfaces:interface": {
        "name": "Loopback30",
        "description": "RESTCONF Demo Interface",
        "type": "iana-if-type:softwareLoopback",
        "enabled": True,
        "ietf-ip:ipv4": {
            "address": [
                {
                    "ip": "10.30.30.1",
                    "prefix-length": 32
                }
            ]
        },
        "ietf-ip:ipv6": {
            "address": [
                {
                    "ip": "2001:db8:30::1",
                    "prefix-length": 128
                }
            ]
        }
    }
}

def create_loopback():
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback30"
    response = requests.put(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        data=json.dumps(PAYLOAD),
        verify=False,
        timeout=10,
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("[+] 201 Created — Loopback30 successfully created.")
    elif response.status_code == 204:
        print("[+] 204 No Content — Loopback30 replaced (already existed).")
    else:
        print(f"[!] Unexpected response: {response.text}")
    response.raise_for_status()

if __name__ == "__main__":
    print("=" * 50)
    print("RESTCONF PUT: Create Loopback30 (dual-stack)")
    print("=" * 50)
    create_loopback()
    print("\nVerify with:")
    print("  show interfaces Loopback30")
    print("  show ip interface brief | include Loopback30")
