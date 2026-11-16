
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

import app.approvals.approval_manager as approval_manager_module
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


def test_audit_approval_requested_is_recorded_by_database(
    manager,
    monkeypatch
):
    execution_id = str(uuid4())
    expected_hash = "a" * 64

    monkeypatch.setattr(
        approval_manager_module,
        "calculate_action_hash",
        lambda **kwargs: expected_hash
    )

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "status": "pending"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approval]
    )

    result = manager.request_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description="Excluir dados"
    )

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_request_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_thread_id": "thread-123",
            "p_step_id": 1,
            "p_action_type": "deletion",
            "p_description": "Excluir dados",
            "p_action_hash": expected_hash,
            "p_parameters": {}
        }
    )

    manager.audit_manager.log_event.assert_not_called()


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


def test_request_approval_reports_database_failure(
    manager,
    monkeypatch
):
    execution_id = str(uuid4())

    monkeypatch.setattr(
        approval_manager_module,
        "calculate_action_hash",
        lambda **kwargs: "a" * 64
    )

    manager.client.rpc.return_value.execute.side_effect = RuntimeError(
        "Falha simulada na transação de aprovação e auditoria."
    )

    with pytest.raises(
        RuntimeError,
        match="Falha simulada na transação"
    ):
        manager.request_approval(
            execution_id=execution_id,
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description="Excluir dados"
        )

    manager.client.rpc.assert_called_once()
    manager.audit_manager.log_event.assert_not_called()
