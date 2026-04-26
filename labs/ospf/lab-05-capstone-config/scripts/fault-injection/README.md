# Fault Injection — OSPF Lab 05

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab 05 topology running in EVE-NG
- Python 3.8+
- `netmiko` installed: `pip install netmiko`
- EVE-NG host reachable

## Reset to Known-Good

```
python3 apply_solution.py --host <eve-ng-ip>
```

## Inject a Fault

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
python3 inject_scenario_04.py --host <eve-ng-ip>   # Ticket 4
python3 inject_scenario_05.py --host <eve-ng-ip>   # Ticket 5
```

## Restore

```
python3 apply_solution.py --host <eve-ng-ip>
```

See `workbook.md` Section 9 for the challenge description and diagnosis guidance.
