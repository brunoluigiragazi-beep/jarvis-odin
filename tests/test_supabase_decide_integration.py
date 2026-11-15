
from uuid import uuid4

from app.approvals.approval_manager import ApprovalManager


def test_supabase_decide_approval_and_rejection():
    manager = ApprovalManager()
    client = manager.client

    scenarios = [
        {
            "decision": "approved",
            "expected_event": "approval_approved",
        },
        {
            "decision": "rejected",
            "expected_event": "approval_rejected",
        },
    ]

    created_execution_ids = []

    try:
        for scenario in scenarios:
            execution_id = str(uuid4())
            thread_id = f"integration-test-{uuid4()}"

            approval = (
                client
                .table("odin_approvals")
                .insert({
                    "execution_id": execution_id,
                    "thread_id": thread_id,
                    "step_id": 1,
                    "action_type": "communication",
                    "description": "Teste de integração de decisão",
                    "parameters": {},
                    "status": "pending",
                })
                .execute()
            )

            assert approval.data, (
                "Não foi possível criar a aprovação de teste."
            )

            created_execution_ids.append(execution_id)

            result = manager.decide(
                execution_id=execution_id,
                decision=scenario["decision"],
                decision_by="ODIN_INTEGRATION_TEST",
            )

            assert result["execution_id"] == execution_id
            assert result["status"] == scenario["decision"]
            assert result["decision_by"] == "ODIN_INTEGRATION_TEST"
            assert result["decided_at"] is not None

            audit = (
                client
                .table("odin_audit_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .eq("event_type", scenario["expected_event"])
                .execute()
            )

            assert len(audit.data) == 1, (
                "O evento de auditoria não foi registrado exatamente uma vez."
            )

            # Uma segunda decisão não pode processar a mesma solicitação.
            try:
                manager.decide(
                    execution_id=execution_id,
                    decision=scenario["decision"],
                    decision_by="ODIN_INTEGRATION_TEST",
                )
            except ValueError:
                pass
            else:
                raise AssertionError(
                    "O sistema aceitou uma segunda decisão."
                )

            # A segunda tentativa não pode duplicar a auditoria.
            audit_after_retry = (
                client
                .table("odin_audit_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .eq("event_type", scenario["expected_event"])
                .execute()
            )

            assert len(audit_after_retry.data) == 1

    finally:
        # Remove somente os registros criados por este teste.
        for execution_id in created_execution_ids:
            (
                client
                .table("odin_audit_logs")
                .delete()
                .eq("execution_id", execution_id)
                .execute()
            )

            (
                client
                .table("odin_approvals")
                .delete()
                .eq("execution_id", execution_id)
                .execute()
            )
