# Fault Restore — SD-Networking Lab 05 (Capstone II)

This lab loads a pre-broken configuration via `setup_lab.py`. Five concurrent faults
are pre-injected across the SD-WAN fabric. Work through the troubleshooting tickets
in `workbook.md` Section 9 before using this restore script.

## Prerequisites

- Python 3.x with `netmiko` installed (`pip install netmiko`)
- EVE-NG lab running with all nodes powered on
- Update the `port` values in `VIPTELA_DEVICES` at the top of `apply_solution.py`
  to match the console ports shown in your EVE-NG web UI

## Restore to Known-Good

```
python3 apply_solution.py
python3 apply_solution.py --host <eve-ng-ip>
```

This restores all five Viptela devices to the fully working solution state.
Run `setup_lab.py` again to reload the pre-broken state for another troubleshooting attempt.

## Troubleshooting Tickets

See `workbook.md` Section 9 for all five tickets and their success criteria.
