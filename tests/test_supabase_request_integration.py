
from uuid import uuid4

import pytest

from app.approvals.approval_manager import ApprovalManager


def test_supabase_request_approval_integration():
    manager = ApprovalManager()

    execution_id = str(uuid4())
    thread_id = f"test-request-{uuid4()}"

    approval_created = False

    try:
        # 1. Criar solicitação real pelo RPC
        approval = manager.request_approval(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=1,
            action_type="deletion",
            description="Teste de integração ODIN",
            parameters={"test": True}
        )

        approval_created = True

        assert approval["execution_id"] == execution_id
        assert approval["thread_id"] == thread_id
        assert approval["step_id"] == 1
        assert approval["action_type"] == "deletion"
        assert approval["status"] == "pending"

        # 2. Consultar evento de auditoria
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
        assert audit_event["details"]["step_id"] == 1
        assert audit_event["details"]["action_type"] == "deletion"
        assert audit_event["details"]["status"] == "pending"

        # 3. Tentar criar novamente com o mesmo execution_id
        duplicate_rejected = False

        try:
            manager.request_approval(
                execution_id=execution_id,
                thread_id=thread_id,
                step_id=1,
                action_type="deletion",
                description="Tentativa duplicada",
                parameters={"test": True}
            )

        except Exception:
            duplicate_rejected = True

        assert duplicate_rejected, (
            "O banco aceitou uma solicitação duplicada."
        )

        # 4. Confirmar que continua existindo somente uma solicitação
        approval_result = (
            manager.client
            .table("odin_approvals")
            .select("id,execution_id,status")
            .eq("execution_id", execution_id)
            .execute()
        )

        assert len(approval_result.data or []) == 1

        # 5. Confirmar que continua existindo somente um evento
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
        # Limpar somente os registros deste teste.
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
