# Fault Injection — OSPF Lab 06

Each script injects one fault for individual practice. The full capstone starts
from the pre-broken state loaded by `setup_lab.py` in the lab root — that state
has all five faults active simultaneously.

Work through the corresponding ticket in `workbook.md` Section 9 before looking
at the solution.

## Prerequisites

- Lab 06 topology running in EVE-NG
- Python 3.8+
- `netmiko` installed: `pip install netmiko`
- EVE-NG host reachable

## Reset to Known-Good (Solution State)

```
python3 apply_solution.py --host <eve-ng-ip>
```

## Inject a Single Fault (Individual Practice)

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
python3 inject_scenario_04.py --host <eve-ng-ip>   # Ticket 4
python3 inject_scenario_05.py --host <eve-ng-ip>   # Ticket 5
```

## Full Capstone (All 5 Faults Concurrent)

```
python3 ../../setup_lab.py --host <eve-ng-ip>
```

See `workbook.md` Section 9 for diagnosis guidance.
