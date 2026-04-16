# Fault Injection -- OSPF Lab 00: Single-Area OSPFv2 Fundamentals

Each script in this directory injects one pre-designed fault into the running
EVE-NG lab. Work through the corresponding ticket in `workbook.md` Section 9
using only the symptom information provided there. Do not read any script
source file until you have independently diagnosed and resolved the fault --
the scripts are the answer key, and reading them first defeats the purpose of
the exercise.

## Prerequisites

- EVE-NG lab `ospf/lab-00-single-area-ospfv2.unl` imported and **STARTED**
- EVE-NG REST credentials are admin/eve (the default)
- `pip install netmiko requests` (or `pip install -r requirements.txt`)

Console ports are discovered automatically via the EVE-NG REST API -- no need
to edit port numbers in any script.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject one scenario at a time
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 -- R4 cannot reach R1 loopback
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 -- No adjacency between R4 and R2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 -- PC1 cannot reach PC2

# 3. Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>
```

## Arguments

All scripts accept the same base arguments:

- `--host <ip>` (required): EVE-NG server IP
- `--lab-path <path>`: Path of the .unl on EVE-NG (default:
  `ospf/lab-00-single-area-ospfv2.unl`). Override if you imported the lab
  to a different folder.

Inject scripts additionally accept:

- `--skip-preflight`: Bypass the sanity check that confirms the target is
  currently in the expected solution state. Use only if you know what you're
  doing.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | At least one device failed to restore (`apply_solution.py` only) |
| `2` | Missing `--host` |
| `3` | EVE-NG API error (lab not running, auth failed, node not found) |
| `4` | Pre-flight check failed (target not in expected solution state) |
