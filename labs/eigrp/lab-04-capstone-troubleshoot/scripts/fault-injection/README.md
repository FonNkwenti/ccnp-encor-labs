# Fault Injection -- EIGRP Lab 04 (Capstone II)

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab booted with all four routers reachable
- `python3 setup_lab.py --host <eve-ng-ip>` loads the full pre-broken state (all 5 faults)
- Solution state restored between individual injections:
  `python3 apply_solution.py --host <eve-ng-ip>`

## Inject a Fault

```bash
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3
python3 inject_scenario_04.py   # Ticket 4
python3 inject_scenario_05.py   # Ticket 5
```

## Restore

```bash
python3 apply_solution.py
```
