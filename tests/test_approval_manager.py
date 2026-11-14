
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.approvals.approval_manager import ApprovalManager


@pytest.fixture
def manager():
    instance = ApprovalManager.__new__(ApprovalManager)

    table = MagicMock()

    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.order.return_value = table
    table.insert.return_value = table
    table.update.return_value = table

    instance.client = MagicMock()
    instance.client.table.return_value = table

    instance.mock_table = table

    return instance


def test_rejects_incomplete_approval(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id="",
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description="Excluir dados"
        )


def test_rejects_invalid_step_id(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=0,
            action_type="deletion",
            description="Excluir dados"
        )


def test_rejects_invalid_parameters(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description="Excluir dados",
            parameters="inválido"
        )


def test_rejects_invalid_decision(manager):
    with pytest.raises(ValueError):
        manager.decide(
            execution_id=str(uuid4()),
            decision="executed",
            decision_by="Bruno"
        )


def test_rejects_empty_decision_by(manager):
    with pytest.raises(ValueError):
        manager.decide(
            execution_id=str(uuid4()),
            decision="approved",
            decision_by=" "
        )


def test_registers_approval_successfully(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "step_id": 1,
        "action_type": "deletion",
        "description": "Excluir dados",
        "parameters": {"table": "odin_memory"},
        "status": "pending"
    }

    manager.mock_table.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[approval])
    ]

    result = manager.request_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description="Excluir dados",
        parameters={"table": "odin_memory"}
    )

    assert result == approval
    manager.mock_table.insert.assert_called_once()


def test_rejects_duplicate_approval(manager):
    execution_id = str(uuid4())

    manager.mock_table.execute.return_value = MagicMock(
        data=[{"id": "existing", "status": "pending"}]
    )

    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id=execution_id,
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description="Excluir dados"
        )

    manager.mock_table.insert.assert_not_called()


def test_lists_pending_approvals(manager):
    pending = [
        {"execution_id": str(uuid4()), "status": "pending"},
        {"execution_id": str(uuid4()), "status": "pending"}
    ]

    manager.mock_table.execute.return_value = MagicMock(data=pending)

    result = manager.get_pending(thread_id="thread-123", limit=10)

    assert result == pending
    manager.mock_table.eq.assert_any_call("status", "pending")
    manager.mock_table.eq.assert_any_call("thread_id", "thread-123")
    manager.mock_table.limit.assert_called_once_with(10)


def test_approves_pending_execution(manager):
    execution_id = str(uuid4())

    approved = {
        "execution_id": execution_id,
        "status": "approved",
        "decision_by": "Bruno"
    }

    manager.mock_table.execute.return_value = MagicMock(data=[approved])

    result = manager.decide(
        execution_id=execution_id,
        decision="approved",
        decision_by="Bruno"
    )

    assert result["status"] == "approved"

    update_data = manager.mock_table.update.call_args.args[0]

    assert update_data["status"] == "approved"
    assert update_data["decision_by"] == "Bruno"

    timestamp = datetime.fromisoformat(update_data["decided_at"])
    assert timestamp.tzinfo is not None


def test_rejects_already_processed_approval(manager):
    execution_id = str(uuid4())

    manager.mock_table.execute.return_value = MagicMock(data=[])

    with pytest.raises(ValueError):
        manager.decide(
            execution_id=execution_id,
            decision="approved",
            decision_by="Bruno"
        )

def test_claims_approved_execution(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "step_id": 1,
        "action_type": "deletion",
        "status": "executing"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approval]
    )

    result = manager.claim_approval(execution_id)

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_claim_approval",
        {"p_execution_id": execution_id}
    )


def test_claim_returns_none_when_not_available(manager):
    execution_id = str(uuid4())

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[]
    )

    result = manager.claim_approval(execution_id)

    assert result is None


def test_claim_rejects_invalid_uuid(manager):
    with pytest.raises(ValueError):
        manager.claim_approval("uuid-invalido")


def test_claim_cannot_be_reused(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "status": "executing"
    }

    rpc_result = manager.client.rpc.return_value.execute

    rpc_result.side_effect = [
        MagicMock(data=[approval]),
        MagicMock(data=[])
    ]

    first_result = manager.claim_approval(execution_id)
    second_result = manager.claim_approval(execution_id)

    assert first_result == approval
    assert second_result is None
