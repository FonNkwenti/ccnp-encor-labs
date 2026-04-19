# Fault Injection — Network Assurance Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab started with all nodes running
- Python 3.8+ with `netmiko` installed (`pip install netmiko`)
- Network connectivity to your EVE-NG server

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore to Known-Good State

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Run `apply_solution.py` before each new ticket to ensure a clean starting state.
