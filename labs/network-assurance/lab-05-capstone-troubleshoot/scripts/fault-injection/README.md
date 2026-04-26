# Fault Injection — Network Assurance Lab 05

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `ccnp-encor/network-assurance/lab-05-capstone-troubleshoot.unl` is running
- All nodes (R1, R2, R3, SW1, SW2) are started in the EVE-NG web UI
- Python 3 with `netmiko` installed: `pip install netmiko`
- EVE-NG REST API accessible on your EVE-NG server IP

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
python3 inject_scenario_04.py --host <eve-ng-ip>   # Ticket 4
python3 inject_scenario_05.py --host <eve-ng-ip>   # Ticket 5
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Use `--reset` for a guaranteed clean slate (erases device config before pushing solution):

```bash
python3 apply_solution.py --host <eve-ng-ip> --reset
```

## Full Pre-Broken State (All 5 Faults Simultaneously)

To load all five faults at once (capstone experience), run setup_lab.py from the lab root:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

## Notes

- Console ports are discovered automatically via the EVE-NG REST API.
- Scripts are idempotent — safe to run multiple times.
- See `workbook.md` Section 9 for the troubleshooting challenges.
- Each inject script starts from the known-good state — run `apply_solution.py` between tickets.
