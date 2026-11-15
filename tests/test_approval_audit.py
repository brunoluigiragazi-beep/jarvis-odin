
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
    table.insert.return_value = table

    instance.client = MagicMock()
    instance.client.table.return_value = table
    instance.mock_table = table

    instance.audit_manager = MagicMock()

    return instance


def test_audit_approval_requested(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "status": "pending"
    }

    manager.mock_table.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[approval])
    ]

    manager.request_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description="Excluir dados"
    )

    manager.audit_manager.log_event.assert_called_once()

    event = manager.audit_manager.log_event.call_args.kwargs

    assert event["event_type"] == "approval_requested"
    assert event["execution_id"] == execution_id
    assert event["thread_id"] == "thread-123"


def test_audit_approval_approved_is_recorded_by_database(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "status": "approved"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approval]
    )

    result = manager.decide(
        execution_id=execution_id,
        decision="approved",
        decision_by="Bruno"
    )

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_decide_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_decision": "approved",
            "p_decision_by": "Bruno"
        }
    )

    # A auditoria é gravada dentro da transação PostgreSQL.
    # O Python não deve registrar um segundo evento.
    manager.audit_manager.log_event.assert_not_called()


def test_audit_approval_rejected_is_recorded_by_database(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "status": "rejected"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approval]
    )

    result = manager.decide(
        execution_id=execution_id,
        decision="rejected",
        decision_by="Bruno"
    )

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_decide_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_decision": "rejected",
            "p_decision_by": "Bruno"
        }
    )

    manager.audit_manager.log_event.assert_not_called()


def test_audit_failure_is_reported(manager):
    execution_id = str(uuid4())

    manager.mock_table.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{
            "execution_id": execution_id,
            "thread_id": "thread-123",
            "status": "pending"
        }])
    ]

    manager.audit_manager.log_event.side_effect = RuntimeError(
        "Falha simulada de auditoria"
    )

    with pytest.raises(RuntimeError, match="falha ao registrar"):
        manager.request_approval(
            execution_id=execution_id,
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description="Excluir dados"
        )
