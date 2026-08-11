from unittest.mock import Mock, patch

from shared.homekit_bridge import trigger_accessory


def test_trigger_accessory_success():
    fake_response = Mock()
    fake_response.raise_for_status = Mock()
    with patch("requests.get", return_value=fake_response) as mock_get:
        result = trigger_accessory("tradingview")

    assert result == {"ok": True, "accessory_id": "tradingview"}
    mock_get.assert_called_once_with(
        "http://127.0.0.1:51828/",
        params={"accessoryId": "tradingview", "state": "true"},
        timeout=5,
    )


def test_trigger_accessory_fails_closed_when_homebridge_unreachable():
    import requests

    with patch("requests.get", side_effect=requests.RequestException("connection refused")):
        result = trigger_accessory("tradingview")

    assert result["ok"] is False
    assert "Homebridge webhook call failed" in result["reason"]


def test_trigger_accessory_respects_custom_webhook_url(monkeypatch):
    monkeypatch.setenv("HOMEKIT_WEBHOOK_URL", "http://127.0.0.1:9999")
    fake_response = Mock()
    fake_response.raise_for_status = Mock()
    with patch("requests.get", return_value=fake_response) as mock_get:
        trigger_accessory("tradingview")

    mock_get.assert_called_once_with(
        "http://127.0.0.1:9999/",
        params={"accessoryId": "tradingview", "state": "true"},
        timeout=5,
    )
