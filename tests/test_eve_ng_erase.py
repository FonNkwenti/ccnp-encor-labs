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
