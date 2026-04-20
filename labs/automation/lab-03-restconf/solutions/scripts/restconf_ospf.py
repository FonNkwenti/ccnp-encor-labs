#!/usr/bin/env python3
"""
RESTCONF PATCH — Add Loopback30 network to OSPF process 1 on R1.

Task 7 solution: adds network 10.30.30.1/0.0.0.0 area 0 to OSPF 1 via
Cisco-IOS-XE-native YANG model.

Verify the result with:
  R1# show run | section ospf
  R1# show ip ospf database
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

OSPF_PAYLOAD = {
    "Cisco-IOS-XE-ospf:ospf": [
        {
            "id": 1,
            "network": [
                {
                    "ip": "10.30.30.1",
                    "mask": "0.0.0.0",
                    "area": 0
                }
            ]
        }
    ]
}

def add_ospf_network():
    url = f"{BASE_URL}/Cisco-IOS-XE-native:native/router/ospf=1"
    response = requests.patch(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        data=json.dumps(OSPF_PAYLOAD),
        verify=False,
        timeout=10,
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print("[+] 204 No Content — OSPF network statement added.")
    elif response.status_code == 404:
        print("[!] 404 Not Found — OSPF process 1 not found. Check IOS-XE YANG path.")
        print("     Try: GET /restconf/data/Cisco-IOS-XE-native:native/router/ospf")
    else:
        print(f"[!] Response: {response.text}")

def verify_ospf():
    url = f"{BASE_URL}/Cisco-IOS-XE-native:native/router/ospf=1"
    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        verify=False,
        timeout=10,
    )
    if response.status_code == 200:
        data = response.json()
        print("\n[*] OSPF 1 config (RESTCONF GET):")
        print(json.dumps(data, indent=2))
    else:
        print(f"[!] GET failed: {response.status_code}")

if __name__ == "__main__":
    print("=" * 50)
    print("RESTCONF PATCH: Add OSPF network statement")
    print("=" * 50)
    add_ospf_network()
    print()
    verify_ospf()
    print("\nCLI verification:")
    print("  R1# show run | section ospf")
    print("  Look for: network 10.30.30.1 0.0.0.0 area 0")
