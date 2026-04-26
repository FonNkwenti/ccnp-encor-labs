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
