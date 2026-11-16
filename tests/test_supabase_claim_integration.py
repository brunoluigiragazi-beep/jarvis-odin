
import uuid

from app.approvals.approval_manager import ApprovalManager
from app.security.action_integrity import calculate_action_hash


def test_supabase_claim_approval_integration():
    manager = ApprovalManager()

    execution_id = str(uuid.uuid4())
    thread_id = f"odin-integration-test-{uuid.uuid4()}"
    step_id = 987654
    action_type = "deletion"
    description = "Teste de integração ODIN"
    parameters = {"test": True}

    try:
        # 1. Calcular a assinatura HMAC da ação.
        action_hash = calculate_action_hash(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        # 2. Criar aprovação exclusiva de teste.
        created = (
            manager.client
            .table("odin_approvals")
            .insert({
                "execution_id": execution_id,
                "thread_id": thread_id,
                "step_id": step_id,
                "action_type": action_type,
                "description": description,
                "parameters": parameters,
                "action_hash": action_hash,
                "status": "approved",
                "decision_by": "ODIN_TEST"
            })
            .execute()
        )

        assert created.data

        # 3. Reivindicar aprovação pela aplicação Python.
        claimed = manager.claim_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        assert claimed is not None
        assert str(claimed["execution_id"]) == execution_id
        assert claimed["thread_id"] == thread_id
        assert claimed["step_id"] == step_id
        assert claimed["action_type"] == action_type
        assert claimed["description"] == description
        assert claimed["parameters"] == parameters
        assert claimed["status"] == "executing"
        assert claimed["action_hash"] == action_hash

        # 4. Tentar reivindicar novamente.
        second_claim = manager.claim_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        assert second_claim is None

        # 5. Verificar auditoria.
        audit = (
            manager.client
            .table("odin_audit_logs")
            .select("id,event_type")
            .eq("execution_id", execution_id)
            .eq("event_type", "approval_claimed")
            .execute()
        )

        assert len(audit.data or []) == 1

    finally:
        # 6. Limpar exclusivamente os registros deste teste.
        # A aprovação é removida mesmo se a limpeza da auditoria falhar.
        try:
            (
                manager.client
                .table("odin_audit_logs")
                .delete()
                .eq("execution_id", execution_id)
                .eq("event_type", "approval_claimed")
                .execute()
            )
        finally:
            (
                manager.client
                .table("odin_approvals")
                .delete()
                .eq("execution_id", execution_id)
                .execute()
            )
