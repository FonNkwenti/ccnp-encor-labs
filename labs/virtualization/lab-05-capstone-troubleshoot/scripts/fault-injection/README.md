# Fault Injection — Virtualization Lab 05

This is a Capstone II (troubleshooting) lab. The **initial configs already contain
the faults** — there are no separate inject scripts. Run `setup_lab.py` to load the
pre-broken state, then work through the tickets in `workbook.md` Section 9.

## Prerequisites

- EVE-NG lab started with all nodes powered on
- Python 3 with the `netmiko` package installed
- EVE-NG server reachable on the network

## Load the Broken State

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

## Restore to Known-Good

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
```

Run the restore script to verify your fixes match the reference solution, or to
reset the lab for another troubleshooting attempt.

## Notes

- All scripts require `--host` to be set to your EVE-NG server's IP address.
- Console ports are discovered automatically via the EVE-NG REST API.
- See `workbook.md` Section 9 for the five troubleshooting tickets.
