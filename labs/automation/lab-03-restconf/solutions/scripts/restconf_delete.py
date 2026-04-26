#!/usr/bin/env python3
"""
RESTCONF DELETE — Remove Loopback30 from R1.

Task 5 solution: sends DELETE to /restconf/data/ietf-interfaces:interfaces/interface=Loopback30
HTTP 204 No Content = successful deletion.
HTTP 404 Not Found = interface does not exist (already deleted or never created).
"""

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP = "10.1.12.1"
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

BASE_URL = f"https://{ROUTER_IP}/restconf/data"
HEADERS = {
    "Accept": "application/yang-data+json",
}

def delete_loopback():
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback30"
    response = requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
        headers=HEADERS,
        verify=False,
        timeout=10,
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print("[+] 204 No Content — Loopback30 deleted successfully.")
    elif response.status_code == 404:
        print("[!] 404 Not Found — Loopback30 does not exist.")
    else:
        print(f"[!] Unexpected response ({response.status_code}): {response.text}")

if __name__ == "__main__":
    print("=" * 50)
    print("RESTCONF DELETE: Remove Loopback30")
    print("=" * 50)
    delete_loopback()
    print("\nVerify with:")
    print("  show interfaces Loopback30")
    print("  (should return '% Invalid input detected' or equivalent error)")
