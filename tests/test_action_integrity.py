import pytest

from app.security.action_integrity import (
    canonicalize_action,
    calculate_action_hash,
    verify_action_hash
)


@pytest.fixture
def action():
    return {
        "execution_id": "12345678-1234-5678-1234-567812345678",
        "thread_id": "thread-test",
        "step_id": 1,
        "action_type": "deletion",
        "description": "Excluir registro de teste",
        "parameters": {
            "expected_result": "Registro removido"
        }
    }


def test_generates_valid_hash(action):
    result = calculate_action_hash(**action)

    assert len(result) == 64


def test_validates_original_action(action):
    generated_hash = calculate_action_hash(**action)

    assert verify_action_hash(generated_hash, **action) is True


def test_detects_description_tampering(action):
    generated_hash = calculate_action_hash(**action)

    modified = {**action, "description": "Outra ação"}

    assert verify_action_hash(generated_hash, **modified) is False


def test_detects_parameter_tampering(action):
    generated_hash = calculate_action_hash(**action)

    modified = {
        **action,
        "parameters": {"expected_result": "Outro resultado"}
    }

    assert verify_action_hash(generated_hash, **modified) is False


def test_rejects_invalid_hash(action):
    assert verify_action_hash("hash-invalido", **action) is False


def test_canonicalization_is_deterministic(action):
    first = canonicalize_action(**action)

    reordered = {
        **action,
        "parameters": {
            "expected_result": "Registro removido"
        }
    }

    second = canonicalize_action(**reordered)

    assert first == second


def test_rejects_invalid_step_id(action):
    action["step_id"] = True

    with pytest.raises(ValueError):
        canonicalize_action(**action)