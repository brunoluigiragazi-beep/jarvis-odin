
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.approvals.approval_manager import ApprovalManager


ACTION_HASH = "a" * 64
DESCRIPTION = "Excluir dados"
PARAMETERS = {"table": "odin_memory"}


@pytest.fixture
def manager(monkeypatch):
    # Hash determinístico para os testes.
    # Não utiliza nem expõe o segredo do .env.
    monkeypatch.setattr(
        "app.approvals.approval_manager.calculate_action_hash",
        lambda **kwargs: ACTION_HASH
    )

    instance = ApprovalManager.__new__(ApprovalManager)

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.order.return_value = table
    table.insert.return_value = table

    instance.client = MagicMock()
    instance.client.table.return_value = table
    instance.mock_table = table

    return instance


# ==========================================
# TESTES DE SOLICITAÇÃO DE APROVAÇÃO
# ==========================================

def test_rejects_incomplete_approval(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id="",
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description=DESCRIPTION
        )


def test_rejects_invalid_step_id(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=0,
            action_type="deletion",
            description=DESCRIPTION
        )


def test_rejects_invalid_parameters(manager):
    with pytest.raises(ValueError):
        manager.request_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description=DESCRIPTION,
            parameters="inválido"
        )


def test_registers_approval_successfully(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "step_id": 1,
        "action_type": "deletion",
        "description": DESCRIPTION,
        "parameters": PARAMETERS,
        "action_hash": ACTION_HASH,
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
        description=DESCRIPTION,
        parameters=PARAMETERS
    )

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_request_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_thread_id": "thread-123",
            "p_step_id": 1,
            "p_action_type": "deletion",
            "p_description": DESCRIPTION,
            "p_action_hash": ACTION_HASH,
            "p_parameters": PARAMETERS
        }
    )


def test_rejects_duplicate_approval(manager):
    execution_id = str(uuid4())

    # Simula uma RPC que não conseguiu registrar a aprovação.
    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with pytest.raises(
        RuntimeError,
        match="Não foi possível registrar a aprovação"
    ):
        manager.request_approval(
            execution_id=execution_id,
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description=DESCRIPTION,
            parameters=PARAMETERS
        )

    manager.client.rpc.assert_called_once()


# ==========================================
# TESTES DE CONSULTA DE APROVAÇÕES
# ==========================================

def test_lists_pending_approvals(manager):
    pending = [
        {"execution_id": str(uuid4()), "status": "pending"},
        {"execution_id": str(uuid4()), "status": "pending"}
    ]

    manager.mock_table.execute.return_value = MagicMock(
        data=pending
    )

    result = manager.get_pending(
        thread_id="thread-123",
        limit=10
    )

    assert result == pending

    manager.mock_table.eq.assert_any_call("status", "pending")
    manager.mock_table.eq.assert_any_call("thread_id", "thread-123")
    manager.mock_table.limit.assert_called_once_with(10)


# ==========================================
# TESTES DE DECISÃO ATÔMICA
# ==========================================

def test_rejects_invalid_decision(manager):
    with pytest.raises(ValueError):
        manager.decide(
            execution_id=str(uuid4()),
            decision="executed",
            decision_by="Bruno"
        )

    manager.client.rpc.assert_not_called()


def test_rejects_empty_decision_by(manager):
    with pytest.raises(ValueError):
        manager.decide(
            execution_id=str(uuid4()),
            decision="approved",
            decision_by=" "
        )

    manager.client.rpc.assert_not_called()


def test_approves_pending_execution(manager):
    execution_id = str(uuid4())

    approved = {
        "execution_id": execution_id,
        "status": "approved",
        "decision_by": "Bruno"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approved]
    )

    result = manager.decide(
        execution_id=execution_id,
        decision="approved",
        decision_by="Bruno"
    )

    assert result == approved

    manager.client.rpc.assert_called_once_with(
        "odin_decide_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_decision": "approved",
            "p_decision_by": "Bruno"
        }
    )


def test_rejects_pending_execution(manager):
    execution_id = str(uuid4())

    rejected = {
        "execution_id": execution_id,
        "status": "rejected",
        "decision_by": "Bruno"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[rejected]
    )

    result = manager.decide(
        execution_id=execution_id,
        decision="rejected",
        decision_by="Bruno"
    )

    assert result == rejected

    manager.client.rpc.assert_called_once_with(
        "odin_decide_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_decision": "rejected",
            "p_decision_by": "Bruno"
        }
    )


def test_rejects_already_processed_approval(manager):
    execution_id = str(uuid4())

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with pytest.raises(ValueError):
        manager.decide(
            execution_id=execution_id,
            decision="approved",
            decision_by="Bruno"
        )


def test_decide_rejects_invalid_uuid(manager):
    with pytest.raises(ValueError):
        manager.decide(
            execution_id="uuid-invalido",
            decision="approved",
            decision_by="Bruno"
        )

    manager.client.rpc.assert_not_called()


# ==========================================
# TESTES DE RESERVA DE APROVAÇÃO
# ==========================================

def test_claims_approved_execution(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "step_id": 1,
        "action_type": "deletion",
        "description": DESCRIPTION,
        "parameters": PARAMETERS,
        "action_hash": ACTION_HASH,
        "status": "executing"
    }

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[approval]
    )

    result = manager.claim_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description=DESCRIPTION,
        parameters=PARAMETERS
    )

    assert result == approval

    manager.client.rpc.assert_called_once_with(
        "odin_claim_approval_v2",
        {
            "p_execution_id": execution_id,
            "p_thread_id": "thread-123",
            "p_step_id": 1,
            "p_action_type": "deletion",
            "p_description": DESCRIPTION,
            "p_parameters": PARAMETERS,
            "p_action_hash": ACTION_HASH
        }
    )


def test_claim_returns_none_when_not_available(manager):
    execution_id = str(uuid4())

    manager.client.rpc.return_value.execute.return_value = MagicMock(
        data=[]
    )

    result = manager.claim_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description=DESCRIPTION,
        parameters=PARAMETERS
    )

    assert result is None


def test_claim_rejects_invalid_uuid(manager):
    with pytest.raises(ValueError):
        manager.claim_approval(
            execution_id="uuid-invalido",
            thread_id="thread-123",
            step_id=1,
            action_type="deletion",
            description=DESCRIPTION,
            parameters=PARAMETERS
        )

    manager.client.rpc.assert_not_called()


def test_claim_rejects_invalid_step_id(manager):
    with pytest.raises(ValueError):
        manager.claim_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=True,
            action_type="deletion",
            description=DESCRIPTION,
            parameters=PARAMETERS
        )

    manager.client.rpc.assert_not_called()


def test_claim_rejects_empty_thread_id(manager):
    with pytest.raises(ValueError):
        manager.claim_approval(
            execution_id=str(uuid4()),
            thread_id=" ",
            step_id=1,
            action_type="deletion",
            description=DESCRIPTION,
            parameters=PARAMETERS
        )

    manager.client.rpc.assert_not_called()


def test_claim_rejects_empty_action_type(manager):
    with pytest.raises(ValueError):
        manager.claim_approval(
            execution_id=str(uuid4()),
            thread_id="thread-123",
            step_id=1,
            action_type=" ",
            description=DESCRIPTION,
            parameters=PARAMETERS
        )

    manager.client.rpc.assert_not_called()


def test_claim_cannot_be_reused(manager):
    execution_id = str(uuid4())

    approval = {
        "execution_id": execution_id,
        "thread_id": "thread-123",
        "step_id": 1,
        "action_type": "deletion",
        "description": DESCRIPTION,
        "parameters": PARAMETERS,
        "action_hash": ACTION_HASH,
        "status": "executing"
    }

    rpc_execute = manager.client.rpc.return_value.execute

    rpc_execute.side_effect = [
        MagicMock(data=[approval]),
        MagicMock(data=[])
    ]

    first_result = manager.claim_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description=DESCRIPTION,
        parameters=PARAMETERS
    )

    second_result = manager.claim_approval(
        execution_id=execution_id,
        thread_id="thread-123",
        step_id=1,
        action_type="deletion",
        description=DESCRIPTION,
        parameters=PARAMETERS
    )

    assert first_result == approval
    assert second_result is None
    assert manager.client.rpc.call_count == 2
