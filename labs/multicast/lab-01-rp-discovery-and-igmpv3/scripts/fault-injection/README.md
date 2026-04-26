# Fault Injection — Multicast Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites
- Lab booted in EVE-NG at `multicast/lab-01-rp-discovery-and-igmpv3.unl`
- `initial-configs/` applied via `setup_lab.py`

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
