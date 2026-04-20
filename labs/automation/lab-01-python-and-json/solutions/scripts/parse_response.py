#!/usr/bin/env python3
"""Task 4 solution: parse JSON response with json.loads()."""

import json

SAMPLE_RESPONSE = """{
  "ietf-interfaces:interfaces": {
    "interface": [
      {
        "name": "GigabitEthernet1",
        "description": "To R2",
        "type": "iana-if-type:ethernetCsmacd",
        "enabled": true,
        "ietf-ip:ipv4": {
          "address": [{"ip": "10.1.12.1", "prefix-length": 30}]
        }
      },
      {
        "name": "Loopback0",
        "description": "",
        "type": "iana-if-type:softwareLoopback",
        "enabled": true,
        "ietf-ip:ipv4": {
          "address": [{"ip": "1.1.1.1", "prefix-length": 32}]
        }
      }
    ]
  }
}"""

data       = json.loads(SAMPLE_RESPONSE)
interfaces = data["ietf-interfaces:interfaces"]["interface"]

for iface in interfaces:
    name     = iface["name"]
    ipv4_addr = iface["ietf-ip:ipv4"]["address"][0]["ip"]
    print(f"Name: {name}, IPv4: {ipv4_addr}")
