# Fault Injection -- Switching Lab 05: Layer 2 Comprehensive Troubleshooting (Capstone II)

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

Note: unlike the configuration labs, this lab's `setup_lab.py` already
loads the **pre-broken** state (all six faults present simultaneously).
The individual inject scripts here are for focused single-fault practice
after you've solved the full scenario once.

## Prerequisites

- EVE-NG lab `switching/lab-05-capstone-troubleshoot.unl` imported and **STARTED**
- EVE-NG REST credentials are admin/eve (the default)
- `pip install -r requirements.txt` (installs `netmiko` + `requests`)

Console ports are discovered automatically via the EVE-NG REST API -- no need
to edit port numbers in any script.

## Standard Workflow

```bash
# Full scenario (all six faults at once, as in real troubleshooting)
python3 ../../setup_lab.py --host <eve-ng-ip>

# When finished or stuck: restore known-good
python3 apply_solution.py --host <eve-ng-ip>

# Focused single-fault repetition (after solving the full scenario once)
python3 apply_solution.py --host <eve-ng-ip>
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
python3 inject_scenario_04.py --host <eve-ng-ip>   # Ticket 4
python3 inject_scenario_05.py --host <eve-ng-ip>   # Ticket 5
python3 inject_scenario_06.py --host <eve-ng-ip>   # Ticket 6

# Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>
```

## Arguments

All scripts accept the same base arguments:

- `--host <ip>` (default: `192.168.242.128`): EVE-NG server IP
- `--lab-path <path>`: Path of the .unl on EVE-NG (default:
  `switching/lab-05-capstone-troubleshoot.unl`). Override if you imported
  the lab to a different folder.

Inject scripts additionally accept:

- `--skip-preflight`: Bypass the sanity check that confirms the target is
  currently in the expected solution state. Use only if you know what you're
  doing.

## Why the pre-flight check?

Injecting a fault on top of a device that's already broken (or not yet
configured) usually produces confusing symptoms. Each inject script first
reads a target `show running-config ...` and verifies the expected
solution-state config is present. If not, it stops with a clear error
pointing you at `apply_solution.py`.

## Ticket matrix (ops view -- no fault descriptions)

| Scenario | Target device | Inject command |
|----------|---------------|----------------|
| 01 | SW3 | `python3 inject_scenario_01.py --host <eve-ng-ip>` |
| 02 | SW2 | `python3 inject_scenario_02.py --host <eve-ng-ip>` |
| 03 | SW3 | `python3 inject_scenario_03.py --host <eve-ng-ip>` |
| 04 | SW2 | `python3 inject_scenario_04.py --host <eve-ng-ip>` |
| 05 | SW3 | `python3 inject_scenario_05.py --host <eve-ng-ip>` |
| 06 | SW2 | `python3 inject_scenario_06.py --host <eve-ng-ip>` |

Read the workbook's Ticket N narrative for the observable symptoms and the
diagnose/fix workflow. Do NOT read the script docstrings before the ticket --
they spoil the answer.

## Exit codes

- `0` success
- `1` at least one device failed to restore (apply_solution.py only)
- `2` missing `--host`
- `3` EVE-NG API error (lab not running, auth failed, node not found)
- `4` pre-flight check failed (target not in expected state)
