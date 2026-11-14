
from unittest.mock import MagicMock

import app.security.pin_auth as pin_auth


def test_pin_success_generates_audit_event(monkeypatch):
    audit = MagicMock()

    monkeypatch.setattr(
        pin_auth,
        "get_lock_status",
        lambda: (0, 0)
    )
    monkeypatch.setattr(
        pin_auth,
        "read_pin",
        lambda prompt: "12345678"
    )
    monkeypatch.setattr(
        pin_auth,
        "verify_pin",
        lambda pin: True
    )
    monkeypatch.setattr(
        pin_auth,
        "reset_failed_attempts",
        lambda: None
    )

    result = pin_auth.authenticate(audit_manager=audit)

    assert result is True

    audit.log_event.assert_called_once()

    event = audit.log_event.call_args.kwargs

    assert event["event_type"] == "pin_auth_success"
    assert event["actor"] == "ODIN"


def test_pin_failure_generates_audit_event(monkeypatch):
    audit = MagicMock()

    monkeypatch.setattr(
        pin_auth,
        "get_lock_status",
        lambda: (0, 0)
    )

    read_pin_mock = MagicMock(
        side_effect=["00000000", KeyboardInterrupt]
    )

    monkeypatch.setattr(
        pin_auth,
        "read_pin",
        read_pin_mock
    )

    monkeypatch.setattr(
        pin_auth,
        "verify_pin",
        lambda pin: False
    )
    monkeypatch.setattr(
        pin_auth,
        "register_failed_attempt",
        lambda: (1, 0)
    )

    result = pin_auth.authenticate(audit_manager=audit)

    assert result is False

    event = audit.log_event.call_args.kwargs

    assert event["event_type"] == "pin_auth_failure"
    assert event["actor"] == "ODIN"
    assert event["details"]["failed_attempts"] == 1


def test_fifth_failure_generates_lock_event(monkeypatch):
    audit = MagicMock()

    locked_until = 2_000_000_000

    monkeypatch.setattr(
        pin_auth,
        "get_lock_status",
        lambda: (4, 0)
    )
    monkeypatch.setattr(
        pin_auth,
        "read_pin",
        lambda prompt: "00000000"
    )
    monkeypatch.setattr(
        pin_auth,
        "verify_pin",
        lambda pin: False
    )
    monkeypatch.setattr(
        pin_auth,
        "register_failed_attempt",
        lambda: (5, locked_until)
    )
    monkeypatch.setattr(
        pin_auth.time,
        "time",
        lambda: 1_900_000_000
    )

    result = pin_auth.authenticate(audit_manager=audit)

    assert result is False

    events = [
        call.kwargs["event_type"]
        for call in audit.log_event.call_args_list
    ]

    assert "pin_auth_failure" in events
    assert "pin_auth_locked" in events


def test_audit_failure_blocks_authentication(monkeypatch):
    audit = MagicMock()

    audit.log_event.side_effect = RuntimeError(
        "Falha simulada de auditoria"
    )

    monkeypatch.setattr(
        pin_auth,
        "get_lock_status",
        lambda: (0, 0)
    )
    monkeypatch.setattr(
        pin_auth,
        "read_pin",
        lambda prompt: "12345678"
    )
    monkeypatch.setattr(
        pin_auth,
        "verify_pin",
        lambda pin: True
    )
    monkeypatch.setattr(
        pin_auth,
        "reset_failed_attempts",
        lambda: None
    )

    result = pin_auth.authenticate(audit_manager=audit)

    assert result is False

    audit.log_event.assert_called_once()


def test_existing_lock_generates_audit_event(monkeypatch):
    audit = MagicMock()

    monkeypatch.setattr(
        pin_auth,
        "get_lock_status",
        lambda: (5, 2_000_000_000)
    )
    monkeypatch.setattr(
        pin_auth.time,
        "time",
        lambda: 1_900_000_000
    )

    result = pin_auth.authenticate(audit_manager=audit)

    assert result is False

    event = audit.log_event.call_args.kwargs

    assert event["event_type"] == "pin_auth_locked"
    assert event["actor"] == "ODIN"
    assert event["details"]["reason"] == "active_lockout"
