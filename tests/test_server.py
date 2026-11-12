import time

from server import error_message, telemetry_message


def test_telemetry_message_has_the_contract_shape():
    payload = {"telemetry": {}, "status": {"started": True}, "error": {}}

    message = telemetry_message(payload)

    assert message["type"] == "telemetry"
    assert message["version"] == 1
    assert isinstance(message["timestamp"], float)
    assert message["data"] == payload      # the payload is passed through unchanged


def test_error_message_without_any_good_data_has_null_age():
    message = error_message("unreachable", None)

    assert message["type"] == "tss_error"
    assert message["version"] == 1
    assert isinstance(message["timestamp"], float)
    assert message["reason"] == "unreachable"
    assert message["age"] is None
    assert "data" not in message           # error messages carry no data


def test_error_message_age_is_seconds_since_the_last_good_data():
    five_seconds_ago = time.time() - 5

    message = error_message("bad_data", five_seconds_ago)

    assert message["reason"] == "bad_data"
    assert abs(message["age"] - 5) < 0.3
    assert message["age"] == round(message["age"], 1)   # one decimal, as the contract says
