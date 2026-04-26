# Fault Injection -- OSPF Lab 03 (Area Types: Stub, Totally Stubby, and NSSA)

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG reachable; lab imported as `ospf/lab-03-area-types.unl`.
- `python3 setup_lab.py --host <eve-ng-ip>` has pushed initial-configs.
- `python3 apply_solution.py --host <eve-ng-ip>` has applied the full
  lab-03 solution, or the student has reached that state manually.
  Scripts refuse to inject unless the device is in the solution state.

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

Add `--skip-preflight` only if you know why the sanity check is failing.

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```
