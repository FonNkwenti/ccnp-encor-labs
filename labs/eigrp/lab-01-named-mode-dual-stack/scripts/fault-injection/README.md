# Fault Injection -- EIGRP Lab 01

Each script injects one fault for individual practice. Work through the corresponding
ticket in `workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab 01 topology running in EVE-NG
- Python 3.8+
- `netmiko` installed: `pip install netmiko`
- EVE-NG host reachable

## Reset to Known-Good (Solution State)

```
python3 apply_solution.py --host <eve-ng-ip>
```

## Inject a Single Fault

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

See `workbook.md` Section 9 for the symptom descriptions and success criteria.
