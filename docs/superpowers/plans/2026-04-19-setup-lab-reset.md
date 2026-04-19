# Setup Lab Reset Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--reset` flag to every `setup_lab.py` that erases device configs with `write erase` before pushing initial configs, giving students a clean slate when redoing labs.

**Architecture:** A shared `erase_device_config()` helper is added to `labs/common/tools/eve_ng.py` so all 38 lab scripts can import it without duplicating logic. Each `setup_lab.py` gains a `--reset` argparse flag and a Phase 1 reset loop in `main()` that runs before the existing Phase 2 push loop.

**Tech Stack:** Python 3.10+, Netmiko 4.x, pytest, `unittest.mock`

---

## File Map

| File | Change |
|------|--------|
| `labs/common/tools/eve_ng.py` | Add `erase_device_config()` function |
| `requirements.txt` | Add `pytest>=7.0` |
| `tests/conftest.py` | Create — adds common tools to sys.path |
| `tests/test_eve_ng_erase.py` | Create — unit tests for `erase_device_config()` |
| `tests/test_setup_lab_reset.py` | Create — integration tests for `--reset` flag in main() |
| All 38 `labs/*/lab-*/setup_lab.py` | Add import, `--reset` arg, Phase 1 loop |

---

## Task 1: Add `pytest` to requirements and create test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `tests/conftest.py`

- [ ] **Step 1: Add pytest to requirements**

Edit `requirements.txt` to add:

```
netmiko>=4.0
requests>=2.28
PyYAML>=6.0
pytest>=7.0
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

# Make labs/common/tools importable from any test file
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labs" / "common" / "tools"))
```

- [ ] **Step 3: Verify pytest discovers tests**

Run: `pytest tests/ --collect-only`
Expected: `no tests ran` (no tests yet, but no import errors either)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/conftest.py
git commit -m "test: bootstrap pytest and conftest for common tools"
```

---

## Task 2: Add `erase_device_config()` to `eve_ng.py` (TDD)

**Files:**
- Create: `tests/test_eve_ng_erase.py`
- Modify: `labs/common/tools/eve_ng.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_eve_ng_erase.py`:

```python
from unittest.mock import MagicMock, call, patch

from eve_ng import erase_device_config


def test_erase_success_returns_true():
    mock_conn = MagicMock()
    with patch("eve_ng.connect_node", return_value=mock_conn):
        result = erase_device_config("192.168.1.1", "R1", 32769)
    assert result is True


def test_erase_sends_write_erase_and_confirm():
    mock_conn = MagicMock()
    with patch("eve_ng.connect_node", return_value=mock_conn):
        erase_device_config("192.168.1.1", "R1", 32769)
    calls = mock_conn.send_command.call_args_list
    assert calls[0] == call("write erase", expect_string=r"\[confirm\]")
    assert calls[1] == call("\n", expect_string=r"#")


def test_erase_disconnects_on_success():
    mock_conn = MagicMock()
    with patch("eve_ng.connect_node", return_value=mock_conn):
        erase_device_config("192.168.1.1", "R1", 32769)
    mock_conn.disconnect.assert_called_once()


def test_erase_returns_false_on_connection_failure():
    with patch("eve_ng.connect_node", side_effect=Exception("connection refused")):
        result = erase_device_config("192.168.1.1", "R1", 32769)
    assert result is False


def test_erase_returns_false_on_command_failure():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = Exception("timeout")
    with patch("eve_ng.connect_node", return_value=mock_conn):
        result = erase_device_config("192.168.1.1", "R1", 32769)
    assert result is False


def test_erase_disconnects_even_on_command_failure():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = Exception("timeout")
    with patch("eve_ng.connect_node", return_value=mock_conn):
        erase_device_config("192.168.1.1", "R1", 32769)
    mock_conn.disconnect.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_eve_ng_erase.py -v`
Expected: `ImportError` or `AttributeError` — `erase_device_config` does not exist yet.

- [ ] **Step 3: Add `erase_device_config()` to `labs/common/tools/eve_ng.py`**

Append after the `connect_node()` function (after line 160):

```python


def erase_device_config(host: str, name: str, port: int) -> bool:
    """Send 'write erase' to clear a device's startup-config.

    Handles the IOS [confirm] prompt automatically. Returns True on
    success, False on any connection or command failure.
    """
    print(f"[*] {name}: erasing config...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] {name}: connection failed -- {exc}")
        return False
    try:
        conn.send_command("write erase", expect_string=r"\[confirm\]")
        conn.send_command("\n", expect_string=r"#")
        print(f"[+] {name}: config erased.")
        return True
    except Exception as exc:
        print(f"[!] {name}: reset failed -- {exc}")
        return False
    finally:
        conn.disconnect()
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_eve_ng_erase.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add labs/common/tools/eve_ng.py tests/test_eve_ng_erase.py
git commit -m "feat: add erase_device_config() helper to eve_ng"
```

---

## Task 3: Update reference lab + integration tests for `--reset` flag

**Files:**
- Modify: `labs/ospf/lab-00-single-area-ospfv2/setup_lab.py`
- Create: `tests/test_setup_lab_reset.py`

- [ ] **Step 1: Write failing integration tests**

Create `tests/test_setup_lab_reset.py`:

```python
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Point at the reference lab's setup_lab so we can import main()
LAB_DIR = Path(__file__).resolve().parents[1] / "labs" / "ospf" / "lab-00-single-area-ospfv2"
sys.path.insert(0, str(LAB_DIR))
sys.path.insert(0, str(LAB_DIR.parents[2] / "common" / "tools"))

import setup_lab  # noqa: E402
from setup_lab import main  # noqa: E402

FAKE_PORTS = {"R1": 32769, "R2": 32770, "R3": 32771, "R4": 32772, "R5": 32773}


def test_reset_flag_calls_erase_before_push(monkeypatch):
    call_order = []

    def fake_erase(host, name, port):
        call_order.append(("erase", name))
        return True

    def fake_push(host, name, port):
        call_order.append(("push", name))
        return True

    monkeypatch.setattr(sys, "argv", ["setup_lab.py", "--host", "192.168.1.1", "--reset"])
    with patch("setup_lab.discover_ports", return_value=FAKE_PORTS), \
         patch("setup_lab.erase_device_config", side_effect=fake_erase), \
         patch("setup_lab.push_device", side_effect=fake_push):
        result = main()

    assert result == 0
    erases = [name for op, name in call_order if op == "erase"]
    pushes = [name for op, name in call_order if op == "push"]
    # All erases must complete before any push
    assert call_order.index(("erase", "R1")) < call_order.index(("push", "R1"))
    assert set(erases) == {"R1", "R2", "R3", "R4", "R5"}
    assert set(pushes) == {"R1", "R2", "R3", "R4", "R5"}


def test_no_reset_flag_skips_erase(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup_lab.py", "--host", "192.168.1.1"])
    with patch("setup_lab.discover_ports", return_value=FAKE_PORTS), \
         patch("setup_lab.erase_device_config") as mock_erase, \
         patch("setup_lab.push_device", return_value=True):
        result = main()
    assert result == 0
    mock_erase.assert_not_called()


def test_reset_failure_still_pushes_configs(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup_lab.py", "--host", "192.168.1.1", "--reset"])
    with patch("setup_lab.discover_ports", return_value=FAKE_PORTS), \
         patch("setup_lab.erase_device_config", return_value=False), \
         patch("setup_lab.push_device", return_value=True) as mock_push:
        result = main()
    # Push still runs despite reset failures
    assert mock_push.call_count == 5


def test_reset_failure_reflected_in_exit_code(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup_lab.py", "--host", "192.168.1.1", "--reset"])
    with patch("setup_lab.discover_ports", return_value=FAKE_PORTS), \
         patch("setup_lab.erase_device_config", return_value=False), \
         patch("setup_lab.push_device", return_value=True):
        result = main()
    assert result == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_setup_lab_reset.py -v`
Expected: `AttributeError` or `ImportError` — `erase_device_config` not yet imported in setup_lab.py.

- [ ] **Step 3: Update `labs/ospf/lab-00-single-area-ospfv2/setup_lab.py`**

**Change 1** — update the import line (line 24):

Old:
```python
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402
```

New:
```python
from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host  # noqa: E402
```

**Change 2** — add `--reset` to argparse in `main()` (after the `--lab-path` argument):

```python
    parser.add_argument("--reset", action="store_true",
                        help="Erase device configs before pushing initial configs")
```

**Change 3** — add Phase 1 reset loop in `main()`, replacing the current push loop block:

Old:
```python
    fail = 0
    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name}: not found in lab {args.lab_path}")
            fail += 1
            continue
        if not push_device(host, name, port):
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed. Check logs above.")
        return 1
    print("[+] All devices configured. PC1/PC2 load their .vpc files on boot.")
    return 0
```

New:
```python
    fail = 0

    if args.reset:
        print("\nPhase 1: Resetting devices...")
        for name in DEVICES:
            port = ports.get(name)
            if port is None:
                print(f"[!] {name}: not found in lab {args.lab_path} — skipping reset")
                fail += 1
                continue
            if not erase_device_config(host, name, port):
                fail += 1
        print(f"\nPhase 2: Pushing initial configs...")

    for name in DEVICES:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name}: not found in lab {args.lab_path}")
            fail += 1
            continue
        if not push_device(host, name, port):
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed. Check logs above.")
        return 1
    print("[+] All devices configured. PC1/PC2 load their .vpc files on boot.")
    return 0
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_setup_lab_reset.py -v`
Expected: `4 passed`

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: `10 passed` (6 from Task 2 + 4 from Task 3)

- [ ] **Step 6: Commit**

```bash
git add labs/ospf/lab-00-single-area-ospfv2/setup_lab.py tests/test_setup_lab_reset.py
git commit -m "feat: add --reset flag to ospf/lab-00 setup_lab.py"
```

---

## Task 4: Apply `--reset` changes to all remaining OSPF lab scripts

**Files to modify** (apply identical changes as Task 3, Step 3 to each):
- `labs/ospf/lab-00-single-area-ospfv2(demo)/setup_lab.py`
- `labs/ospf/lab-01-multi-area-ospfv2/setup_lab.py`
- `labs/ospf/lab-02-network-types/setup_lab.py`
- `labs/ospf/lab-03-area-types/setup_lab.py`
- `labs/ospf/lab-04-summarization-filtering/setup_lab.py`
- `labs/ospf/lab-05-capstone-config/setup_lab.py`
- `labs/ospf/lab-06-capstone-troubleshoot/setup_lab.py`

Apply the same three changes as Task 3, Step 3 to every file above:

1. Add `erase_device_config` to the `from eve_ng import ...` line
2. Add `parser.add_argument("--reset", action="store_true", help="Erase device configs before pushing initial configs")` after `--lab-path`
3. Replace the `fail = 0` + push loop block with the Phase 1 + Phase 2 version

- [ ] **Step 1: Apply changes to all 7 OSPF scripts**

Edit each file listed above. The three changes are identical to Task 3, Step 3 — only the lab name in the description string differs (which you are not changing).

- [ ] **Step 2: Run full test suite to catch any regressions**

Run: `pytest tests/ -v`
Expected: `10 passed`

- [ ] **Step 3: Commit**

```bash
git add labs/ospf/
git commit -m "feat: add --reset flag to all OSPF lab setup scripts"
```

---

## Task 5: Apply `--reset` changes to switching lab scripts

**Files to modify:**
- `labs/switching/lab-00-vlans-and-trunking/setup_lab.py`
- `labs/switching/lab-01-etherchannel/setup_lab.py`
- `labs/switching/lab-02-rstp-and-enhancements/setup_lab.py`
- `labs/switching/lab-03-mst/setup_lab.py`
- `labs/switching/lab-04-capstone-config/setup_lab.py`
- `labs/switching/lab-05-capstone-troubleshoot/setup_lab.py`

Apply the same three changes as Task 3, Step 3 to every file above.

- [ ] **Step 1: Apply changes to all 6 switching scripts**

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: `10 passed`

- [ ] **Step 3: Commit**

```bash
git add labs/switching/
git commit -m "feat: add --reset flag to all switching lab setup scripts"
```

---

## Task 6: Apply `--reset` changes to EIGRP, BGP, IP-services, multicast, and virtualization scripts

**Files to modify:**

EIGRP:
- `labs/eigrp/lab-00-classic-eigrp/setup_lab.py`
- `labs/eigrp/lab-01-named-mode-dual-stack/setup_lab.py`
- `labs/eigrp/lab-02-stub-summarization-variance/setup_lab.py`
- `labs/eigrp/lab-03-capstone-config/setup_lab.py`
- `labs/eigrp/lab-04-capstone-troubleshoot/setup_lab.py`

BGP:
- `labs/bgp/lab-00-ebgp-peering/setup_lab.py`
- `labs/bgp/lab-01-ibgp-and-dual-stack/setup_lab.py`
- `labs/bgp/lab-02-best-path-selection/setup_lab.py`
- `labs/bgp/lab-03-capstone-config/setup_lab.py`
- `labs/bgp/lab-04-capstone-troubleshoot/setup_lab.py`

IP-services:
- `labs/ip-services/lab-00-ntp-and-qos/setup_lab.py`
- `labs/ip-services/lab-01-nat-pat/setup_lab.py`
- `labs/ip-services/lab-02-hsrp/setup_lab.py`
- `labs/ip-services/lab-03-vrrp-dual-stack/setup_lab.py`
- `labs/ip-services/lab-04-capstone-config/setup_lab.py`
- `labs/ip-services/lab-05-capstone-troubleshoot/setup_lab.py`

Multicast:
- `labs/multicast/lab-00-pim-sm-and-igmp/setup_lab.py`
- `labs/multicast/lab-01-rp-discovery-and-igmpv3/setup_lab.py`
- `labs/multicast/lab-02-ssm-bidir-msdp/setup_lab.py`
- `labs/multicast/lab-03-capstone-config/setup_lab.py`
- `labs/multicast/lab-04-capstone-troubleshoot/setup_lab.py`

Virtualization:
- `labs/virtualization/lab-00-vrf-lite/setup_lab.py`
- `labs/virtualization/lab-01-vrf-dual-stack/setup_lab.py`

Apply the same three changes as Task 3, Step 3 to every file above.

- [ ] **Step 1: Apply changes to all 22 remaining scripts**

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: `10 passed`

- [ ] **Step 3: Commit**

```bash
git add labs/eigrp/ labs/bgp/ labs/ip-services/ labs/multicast/ labs/virtualization/
git commit -m "feat: add --reset flag to EIGRP, BGP, ip-services, multicast, and virtualization setup scripts"
```

---

## Verification

After all tasks complete, verify the feature end-to-end with the test suite:

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_eve_ng_erase.py::test_erase_success_returns_true PASSED
tests/test_eve_ng_erase.py::test_erase_sends_write_erase_and_confirm PASSED
tests/test_eve_ng_erase.py::test_erase_disconnects_on_success PASSED
tests/test_eve_ng_erase.py::test_erase_returns_false_on_connection_failure PASSED
tests/test_eve_ng_erase.py::test_erase_returns_false_on_command_failure PASSED
tests/test_eve_ng_erase.py::test_erase_disconnects_even_on_command_failure PASSED
tests/test_setup_lab_reset.py::test_reset_flag_calls_erase_before_push PASSED
tests/test_setup_lab_reset.py::test_no_reset_flag_skips_erase PASSED
tests/test_setup_lab_reset.py::test_reset_failure_still_pushes_configs PASSED
tests/test_setup_lab_reset.py::test_reset_failure_reflected_in_exit_code PASSED
10 passed
```
