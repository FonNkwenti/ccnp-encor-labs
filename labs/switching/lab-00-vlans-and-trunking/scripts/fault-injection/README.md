# Fault Injection -- Switching Lab 00: VLANs and Trunking

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `switching/lab-00-vlans-and-trunking.unl` imported and **STARTED**
- EVE-NG REST credentials are admin/eve (the default)
- `pip install -r requirements.txt` (installs `netmiko` + `requests`)

Console ports are discovered automatically via the EVE-NG REST API -- no need
to edit port numbers in any script.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject one scenario at a time
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 -- targets SW1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 -- targets SW2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 -- targets SW3

# 3. Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>
```

## Arguments

All scripts accept the same base arguments:

- `--host <ip>` (required): EVE-NG server IP
- `--lab-path <path>`: Path of the .unl on EVE-NG (default:
  `switching/lab-00-vlans-and-trunking.unl`). Override if you imported the lab
  to a different folder.

Inject scripts additionally accept:

- `--skip-preflight`: Bypass the sanity check that confirms the target is
  currently in the expected solution state. Use only if you know what you're
  doing.

## Why the pre-flight check?

Injecting a fault on top of a device that's already broken (or not yet
configured) usually produces confusing symptoms. Each inject script first
reads `show running-config interface <target>` and verifies the expected
solution-state config is present. If not, it stops with a clear error
pointing you at `apply_solution.py`.

## Exit codes

- `0` success
- `1` at least one device failed to restore (apply_solution.py only)
- `2` missing `--host`
- `3` EVE-NG API error (lab not running, auth failed, node not found)
- `4` pre-flight check failed (target not in expected state)
