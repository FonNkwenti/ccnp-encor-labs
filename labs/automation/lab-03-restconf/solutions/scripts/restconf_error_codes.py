#!/usr/bin/env python3
"""
RESTCONF Response Code Demonstrations — Task 6.

Intentionally triggers each HTTP response code so the student can observe
the exact status code, error body, and understand when each occurs.
"""

import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP = "10.1.12.1"
USERNAME = "admin"
PASSWORD = "Encor-API-2026"
WRONG_PASSWORD = "wrong-password"

BASE_URL = f"https://{ROUTER_IP}/restconf/data"
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

def demo_200_get():
    """200 OK — successful GET returns existing data."""
    print("\n--- 200 OK: GET existing interface ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback0"
    r = requests.get(url, auth=(USERNAME, PASSWORD), headers=HEADERS, verify=False, timeout=10)
    print(f"Status: {r.status_code}  (200 = data returned)")

def demo_201_post():
    """201 Created — POST to create a new resource (if it does not exist)."""
    print("\n--- 201 Created: POST to create Loopback31 ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces"
    payload = {
        "ietf-interfaces:interface": {
            "name": "Loopback31",
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {
                "address": [{"ip": "10.31.31.1", "prefix-length": 32}]
            }
        }
    }
    r = requests.post(
        url, auth=(USERNAME, PASSWORD), headers=HEADERS,
        data=json.dumps(payload), verify=False, timeout=10
    )
    print(f"Status: {r.status_code}  (201 = created; 409 = already exists)")
    if r.status_code == 409:
        print("  [409 Conflict] Loopback31 already exists — DELETE it first to get 201.")

def demo_204_delete():
    """204 No Content — successful DELETE returns empty body."""
    print("\n--- 204 No Content: DELETE Loopback31 ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback31"
    r = requests.delete(url, auth=(USERNAME, PASSWORD), headers=HEADERS, verify=False, timeout=10)
    print(f"Status: {r.status_code}  (204 = deleted; 404 = not found)")

def demo_400_bad_request():
    """400 Bad Request — malformed JSON or invalid YANG data."""
    print("\n--- 400 Bad Request: send malformed payload ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback0"
    bad_payload = '{"ietf-interfaces:interface": {"name": "Loopback0", "enabled": "not-a-boolean"}}'
    r = requests.patch(
        url, auth=(USERNAME, PASSWORD), headers=HEADERS,
        data=bad_payload, verify=False, timeout=10
    )
    print(f"Status: {r.status_code}  (400 = server rejected the payload)")

def demo_401_unauthorized():
    """401 Unauthorized — wrong credentials."""
    print("\n--- 401 Unauthorized: wrong password ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces"
    r = requests.get(url, auth=(USERNAME, WRONG_PASSWORD), headers=HEADERS, verify=False, timeout=10)
    print(f"Status: {r.status_code}  (401 = authentication failed)")

def demo_404_not_found():
    """404 Not Found — resource path does not exist."""
    print("\n--- 404 Not Found: GET non-existent interface ---")
    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=Loopback999"
    r = requests.get(url, auth=(USERNAME, PASSWORD), headers=HEADERS, verify=False, timeout=10)
    print(f"Status: {r.status_code}  (404 = resource does not exist)")

if __name__ == "__main__":
    print("=" * 55)
    print("RESTCONF Response Code Demonstrations (Task 6)")
    print("=" * 55)
    demo_200_get()
    demo_201_post()
    demo_204_delete()
    demo_400_bad_request()
    demo_401_unauthorized()
    demo_404_not_found()
    print("\nDone.")
