# Fault Injection -- IP Services Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

1. The lab is running in EVE-NG (`ip-services/lab-02-hsrp.unl`).
2. Initial configs pushed with
   `python3 ../../setup_lab.py --host <eve-ng-ip>`.
3. HSRP tasks 1-6 from `workbook.md` Section 5 completed -- the injectors
   require HSRPv2 groups 1 and 2 plus interface tracking to be configured
   before they can break them.

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
