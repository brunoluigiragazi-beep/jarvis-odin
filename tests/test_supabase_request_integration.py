
from uuid import uuid4

from app.approvals.approval_manager import ApprovalManager
from app.security.action_integrity import calculate_action_hash


def test_supabase_request_approval_integration():
    manager = ApprovalManager()

    execution_id = str(uuid4())
    thread_id = f"test-request-{uuid4()}"
    step_id = 1
    action_type = "deletion"
    description = "Teste de integração ODIN"
    parameters = {"test": True}

    try:
        # 1. Criar solicitação real pelo RPC.
        approval = manager.request_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        assert str(approval["execution_id"]) == execution_id
        assert approval["thread_id"] == thread_id
        assert approval["step_id"] == step_id
        assert approval["action_type"] == action_type
        assert approval["status"] == "pending"

        # 2. Calcular a assinatura esperada.
        expected_hash = calculate_action_hash(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        # 3. Consultar a aprovação armazenada.
        approval_result = (
            manager.client
            .table("odin_approvals")
            .select(
                "execution_id,thread_id,step_id,action_type,"
                "description,parameters,action_hash,status"
            )
            .eq("execution_id", execution_id)
            .execute()
        )

        approval_rows = approval_result.data or []

        assert len(approval_rows) == 1

        stored_approval = approval_rows[0]

        assert stored_approval["action_hash"] == expected_hash
        assert stored_approval["description"] == description
        assert stored_approval["parameters"] == parameters
        assert stored_approval["status"] == "pending"

        # 4. Consultar evento de auditoria.
        audit_result = (
            manager.client
            .table("odin_audit_logs")
            .select("*")
            .eq("execution_id", execution_id)
            .eq("event_type", "approval_requested")
            .execute()
        )

        audit_events = audit_result.data or []

        assert len(audit_events) == 1

        audit_event = audit_events[0]

        assert audit_event["actor"] == "ODIN"
        assert audit_event["thread_id"] == thread_id
        assert audit_event["details"]["step_id"] == step_id
        assert audit_event["details"]["action_type"] == action_type
        assert audit_event["details"]["status"] == "pending"

        # 5. Tentar criar novamente com o mesmo execution_id.
        duplicate_rejected = False

        try:
            manager.request_approval(
                execution_id=execution_id,
                thread_id=thread_id,
                step_id=step_id,
                action_type=action_type,
                description="Tentativa duplicada",
                parameters=parameters
            )
        except RuntimeError:
            duplicate_rejected = True

        assert duplicate_rejected, (
            "O banco aceitou uma solicitação duplicada."
        )

        # 6. Confirmar que continua existindo somente uma solicitação.
        approval_result = (
            manager.client
            .table("odin_approvals")
            .select("id,execution_id,status")
            .eq("execution_id", execution_id)
            .execute()
        )

        assert len(approval_result.data or []) == 1

        # 7. Confirmar que continua existindo somente um evento.
        audit_result = (
            manager.client
            .table("odin_audit_logs")
            .select("id")
            .eq("execution_id", execution_id)
            .eq("event_type", "approval_requested")
            .execute()
        )

        assert len(audit_result.data or []) == 1

    finally:
        # Limpar exclusivamente os registros deste teste.
        # Auditoria primeiro, depois solicitação.
        try:
            (
                manager.client
                .table("odin_audit_logs")
                .delete()
                .eq("execution_id", execution_id)
                .eq("event_type", "approval_requested")
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
