# Fault Injection -- Switching Lab 00: VLANs and Trunking

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

## Before You Begin

Update the `CONSOLE_PORT` value in each script to match your EVE-NG dynamic
telnet ports (visible in the EVE-NG web UI when nodes are running).

## Inject a Fault

```bash
python3 inject_scenario_01.py --host 192.168.x.x   # Ticket 1 — targets SW1
python3 inject_scenario_02.py --host 192.168.x.x   # Ticket 2 — targets SW2
python3 inject_scenario_03.py --host 192.168.x.x   # Ticket 3 — targets SW3
```

## Restore All Devices to Solution State

```bash
python3 apply_solution.py --host 192.168.x.x
```

This pushes the full solution configs from `../../solutions/` to all devices
(SW1, SW2, SW3, R1).
