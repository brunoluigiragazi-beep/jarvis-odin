
import uuid

from app.approvals.approval_manager import ApprovalManager


def test_supabase_claim_approval_integration():
    manager = ApprovalManager()

    execution_id = str(uuid.uuid4())
    thread_id = f"odin-integration-test-{uuid.uuid4()}"
    step_id = 987654
    action_type = "deletion"

    approval_created = False

    try:
        # 1. Criar aprovação exclusiva de teste.
        created = (
            manager.client
            .table("odin_approvals")
            .insert({
                "execution_id": execution_id,
                "thread_id": thread_id,
                "step_id": step_id,
                "action_type": action_type,
                "description": "Teste de integração ODIN",
                "parameters": {"test": True},
                "status": "approved",
                "decision_by": "ODIN_TEST"
            })
            .execute()
        )

        assert created.data
        approval_created = True

        # 2. Reivindicar aprovação pela aplicação Python.
        claimed = manager.claim_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type
        )

        assert claimed is not None
        assert str(claimed["execution_id"]) == execution_id
        assert claimed["thread_id"] == thread_id
        assert claimed["step_id"] == step_id
        assert claimed["action_type"] == action_type
        assert claimed["status"] == "executing"

        # 3. Tentar reivindicar novamente.
        second_claim = manager.claim_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type
        )

        assert second_claim is None

        # 4. Verificar auditoria.
        audit = (
            manager.client
            .table("odin_audit_logs")
            .select("id,event_type")
            .eq("execution_id", execution_id)
            .eq("event_type", "approval_claimed")
            .execute()
        )

        assert len(audit.data) == 1

    finally:
        if approval_created:
            manager.client.table("odin_audit_logs") \
                .delete() \
                .eq("execution_id", execution_id) \
                .eq("event_type", "approval_claimed") \
                .execute()

            manager.client.table("odin_approvals") \
                .delete() \
                .eq("execution_id", execution_id) \
                .execute()
