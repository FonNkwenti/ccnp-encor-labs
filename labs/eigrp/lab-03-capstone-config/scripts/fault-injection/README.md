# Fault Injection -- EIGRP Lab 03

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab running in EVE-NG, all six nodes started (R1-R4 + PC1 + PC2)
- Python 3.9+ with `netmiko` and `requests` installed
- Solution state applied first: `python3 apply_solution.py --host <eve-ng-ip>`

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
