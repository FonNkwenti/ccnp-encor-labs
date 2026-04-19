# Fault Injection — Virtualization Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab topology running in EVE-NG
- Lab must be in **solution state** before each injection
- Python 3 with Netmiko installed (`pip install netmiko`)
- EVE-NG server IP address

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Run restore between tickets so each scenario starts from a clean baseline.
