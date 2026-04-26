# Fault Injection — Virtualization Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `lab-01-vrf-dual-stack.unl` is running
- Devices are in the **solution state** (run `apply_solution.py` first)
- Python 3.8+ with Netmiko installed

## Inject a Fault

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```
python3 apply_solution.py --host <eve-ng-ip>
```
