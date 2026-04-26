# Fault Injection — IP Services Lab 04

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab topology must be running in EVE-NG
- Solution configs must be applied (run `apply_solution.py` for a clean starting state)
- Python dependencies: `pip install netmiko`

## Inject a Fault

```
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3
```

## Restore

```
python3 apply_solution.py
```
