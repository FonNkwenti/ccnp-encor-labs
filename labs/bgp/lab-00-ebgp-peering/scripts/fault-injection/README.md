# Fault Injection -- BGP Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab booted with R1 and R3 both reachable
- `python3 setup_lab.py --host <eve-ng-ip>` loads the solution state first
- Solution state restored between injections:
  `python3 apply_solution.py --host <eve-ng-ip>`

## Inject a Fault

```bash
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py
```
