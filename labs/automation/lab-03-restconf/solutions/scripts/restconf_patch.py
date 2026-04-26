#!/usr/bin/env python3
"""
RESTCONF PATCH — Update the description on Loopback30.

Task 4 solution: sends PATCH to /restconf/data/ietf-interfaces:interfaces/interface=Loopback30
merging only the description field. HTTP 204 No Content indicates success.

PATCH merges into existing data; PUT replaces the entire resource.
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

PATCH_PAYLOAD = {
    "ietf-interfaces:interface": {
        "name": "Loopback30",
        "description": "Updated via RESTCONF PATCH"
    }
}

def patch_description():
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback30"
    response = requests.patch(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        data=json.dumps(PATCH_PAYLOAD),
        verify=False,
        timeout=10,
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print("[+] 204 No Content — description updated successfully.")
    else:
        print(f"[!] Unexpected response: {response.text}")
    response.raise_for_status()

def verify_description():
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback30"
    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        verify=False,
        timeout=10,
    )
    data = response.json()
    iface = data.get("ietf-interfaces:interface", {})
    desc = iface.get("description", "(none)")
    print(f"[*] Current description: '{desc}'")

if __name__ == "__main__":
    print("=" * 50)
    print("RESTCONF PATCH: Update Loopback30 description")
    print("=" * 50)
    patch_description()
    print()
    verify_description()
