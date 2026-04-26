# Fault Injection — Network Assurance Lab 03

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `ccnp-encor/network-assurance/lab-03-ip-sla.unl` is running
- All nodes (R1, R2, R3, SW1, SW2) are started in the EVE-NG web UI
- Python 3 with `netmiko` installed: `pip install netmiko`
- EVE-NG REST API accessible on your EVE-NG server IP

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Use `--reset` for a guaranteed clean slate (erases device config before pushing solution):

```bash
python3 apply_solution.py --host <eve-ng-ip> --reset
```

## Notes

- Console ports are discovered automatically via the EVE-NG REST API.
- Scripts are idempotent — safe to run multiple times.
- See `workbook.md` Section 9 for the troubleshooting challenges.
