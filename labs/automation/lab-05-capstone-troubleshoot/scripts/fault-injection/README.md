# Fault Injection — Automation Lab 05

Lab 05 is a capstone troubleshooting lab. All faults are pre-loaded by `setup_lab.py`
at the beginning of each session. There are no per-ticket inject scripts.

Work through the tickets in `workbook.md` Section 9 before looking at the solutions.

## Prerequisites

- EVE-NG lab running with all nodes started
- `netmiko` installed: `pip install netmiko`
- Console ports populated in `setup_lab.py` and `apply_solution.py`

## Load Pre-Broken State

```
python3 setup_lab.py --host <eve-ng-ip>
```

## Restore Working State

```
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

Run `apply_solution.py` after completing (or abandoning) a session to restore
all devices to a fully functional state before the next attempt.
