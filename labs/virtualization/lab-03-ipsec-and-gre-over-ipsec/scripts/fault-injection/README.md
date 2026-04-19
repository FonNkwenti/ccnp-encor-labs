# Fault Injection -- Virtualization Lab 03

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (discovered automatically via the EVE-NG REST API)
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

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

## Workflow

```bash
# Reset lab to known-good state before each scenario
python3 apply_solution.py --host <eve-ng-ip>

# Inject a fault
python3 inject_scenario_01.py --host <eve-ng-ip>

# Troubleshoot using only show commands (refer to workbook.md Section 9)

# Restore when done
python3 apply_solution.py --host <eve-ng-ip>
```

## Options

All scripts accept the following arguments:

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `192.168.x.x` | EVE-NG server IP address |
| `--lab-path` | (lab default) | Path to the `.unl` file on EVE-NG |
| `--skip-preflight` | off | Skip the known-good state check |
