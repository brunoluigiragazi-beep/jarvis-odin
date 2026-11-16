import hashlib
import hmac
import json

from app.config.settings import get_action_integrity_key


def canonicalize_action(
    execution_id: str,
    thread_id: str,
    step_id: int,
    action_type: str,
    description: str,
    parameters: dict
) -> bytes:

    if not isinstance(parameters, dict):
        raise ValueError("Parâmetros inválidos.")

    if not isinstance(step_id, int) or isinstance(step_id, bool) or step_id < 1:
        raise ValueError("ID da etapa inválido.")

    action = {
        "execution_id": execution_id,
        "thread_id": thread_id,
        "step_id": step_id,
        "action_type": action_type,
        "description": description,
        "parameters": parameters
    }

    return json.dumps(
        action,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")


def calculate_action_hash(
    execution_id: str,
    thread_id: str,
    step_id: int,
    action_type: str,
    description: str,
    parameters: dict
) -> str:

    key = get_action_integrity_key().encode("utf-8")

    payload = canonicalize_action(
        execution_id=execution_id,
        thread_id=thread_id,
        step_id=step_id,
        action_type=action_type,
        description=description,
        parameters=parameters
    )

    return hmac.new(
        key,
        payload,
        hashlib.sha256
    ).hexdigest()


def verify_action_hash(
    expected_hash: str,
    execution_id: str,
    thread_id: str,
    step_id: int,
    action_type: str,
    description: str,
    parameters: dict
) -> bool:

    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return False

    try:
        actual_hash = calculate_action_hash(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(expected_hash, actual_hash)