# Fault Injection -- IP Services Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

1. The lab is running in EVE-NG (`ip-services/lab-01-nat-pat.unl`).
2. Initial configs pushed with
   `python3 ../../setup_lab.py --host <eve-ng-ip>`.
3. NAT tasks 1-5 from `workbook.md` Section 5 completed -- the injectors
   require the NAT inside/outside designations and all three NAT rules
   to exist before they can break them.

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
