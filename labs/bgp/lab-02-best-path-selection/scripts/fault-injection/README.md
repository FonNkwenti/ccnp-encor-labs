# Fault Injection -- BGP Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

1. The lab is running in EVE-NG (`bgp/lab-02-best-path-selection.unl`).
2. Initial configs have been pushed with `python3 ../../setup_lab.py --host <eve-ng-ip>`.
3. Students have completed Section 5 (Core Implementation) so the lab is in the
   solution state before injection. Alternatively, run `python3 apply_solution.py`.

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
