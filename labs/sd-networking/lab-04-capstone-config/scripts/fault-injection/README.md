# Fault Injection Scripts

Scripts to set up troubleshooting scenarios for the SD-WAN Capstone lab.
See workbook.md Section 9 for the challenge descriptions.

---

## Prerequisites

- Python 3.8+
- `netmiko` installed: `pip install netmiko`
- EVE-NG lab running with vSmart and vEdge2 powered on
- Telnet ports for each device visible in the EVE-NG UI

### Set port values before first use

Each script contains module-level port constants. Open each file and update:

| Constant       | Device  | Where to find the value     |
|----------------|---------|-----------------------------|
| `VSMART_PORT`  | vSmart  | EVE-NG node tooltip/console |
| `VEDGE2_PORT`  | vEdge2  | EVE-NG node tooltip/console |

---

## Restore to known-good state (run this first)

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Always restore before injecting a new scenario.

---

## Run a scenario

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>
python3 inject_scenario_02.py --host <eve-ng-ip>
python3 inject_scenario_03.py --host <eve-ng-ip>
```

Default host is `192.168.x.x`. Pass `--host` to override.

---

## Restore after a scenario

```bash
python3 apply_solution.py --host <eve-ng-ip>
```
