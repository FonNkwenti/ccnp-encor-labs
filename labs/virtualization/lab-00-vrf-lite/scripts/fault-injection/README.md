# Fault Injection — Virtualization Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (discovered automatically via EVE-NG API)
- Python 3.x installed
- `netmiko` and `requests` libraries installed (`pip install netmiko requests`)

## Workflow

Reset the lab to a known-good state before each ticket:

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

### Scenario 01

| Field | Value |
|-------|-------|
| Target device | R3 |
| Command | `python3 inject_scenario_01.py --host <eve-ng-ip>` |

### Scenario 02

| Field | Value |
|-------|-------|
| Target devices | R1, R2 |
| Command | `python3 inject_scenario_02.py --host <eve-ng-ip>` |

### Scenario 03

| Field | Value |
|-------|-------|
| Target device | R1 |
| Command | `python3 inject_scenario_03.py --host <eve-ng-ip>` |

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

## Options

All scripts accept:

| Flag | Description |
|------|-------------|
| `--host <ip>` | EVE-NG server IP (required) |
| `--lab-path <path>` | Override the default .unl path on EVE-NG |
| `--skip-preflight` | Skip the pre-run sanity check (inject scripts only) |
