# Fault Injection — Multicast Lab 03 (Capstone I)

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab 03 deployed in EVE-NG at `multicast/lab-03-capstone-config.unl`
- All four routers configured to the solution end-state (run `apply_solution.py`
  first if you want a clean known-good starting point)

## Inject a Fault

```bash
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3
python3 inject_all.py           # all three at once (multi-fault triage)
```

## Restore

```bash
python3 apply_solution.py
```
