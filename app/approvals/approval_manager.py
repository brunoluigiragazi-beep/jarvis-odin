
from datetime import datetime, timezone
from uuid import UUID

from supabase import create_client

from app.config.settings import (
    get_supabase_url,
    get_supabase_key
)
from app.audit.audit_manager import AuditManager


class ApprovalManager:

    def __init__(self, audit_manager=None):
        self.client = create_client(
            get_supabase_url(),
            get_supabase_key()
        )

        self.audit_manager = (
            audit_manager
            if audit_manager is not None
            else AuditManager()
        )

    def _record_audit(
        self,
        event_type,
        execution_id,
        thread_id,
        actor,
        details
    ):
        audit_manager = getattr(self, "audit_manager", None)

        if audit_manager is None:
            return

        try:
            audit_manager.log_event(
                event_type=event_type,
                execution_id=execution_id,
                thread_id=thread_id,
                actor=actor,
                details=details
            )
        except Exception as error:
            raise RuntimeError(
                "A operação foi registrada, mas houve falha "
                "ao registrar o evento de auditoria."
            ) from error

    def request_approval(
        self,
        execution_id,
        thread_id,
        step_id,
        action_type,
        description,
        parameters=None
    ):
        required_fields = {
            "execution_id": execution_id,
            "thread_id": thread_id,
            "action_type": action_type,
            "description": description
        }

        for field, value in required_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Campo obrigatório inválido: {field}."
                )

        try:
            UUID(execution_id)
        except (ValueError, TypeError, AttributeError):
            raise ValueError(
                "ID da execução deve ser um UUID válido."
            )

        if (
            not isinstance(step_id, int)
            or isinstance(step_id, bool)
            or step_id < 1
        ):
            raise ValueError("ID da etapa inválido.")

        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("Parâmetros inválidos.")

        existing = (
            self.client.table("odin_approvals")
            .select("id,status")
            .eq("execution_id", execution_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            raise ValueError(
                "Esta execução já possui uma solicitação de aprovação."
            )

        result = (
            self.client.table("odin_approvals")
            .insert({
                "execution_id": execution_id,
                "thread_id": thread_id.strip(),
                "step_id": step_id,
                "action_type": action_type.strip(),
                "description": description.strip(),
                "parameters": parameters or {},
                "status": "pending"
            })
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Não foi possível registrar a aprovação."
            )

        approval = result.data[0]

        self._record_audit(
            event_type="approval_requested",
            execution_id=execution_id,
            thread_id=thread_id.strip(),
            actor="ODIN",
            details={
                "step_id": step_id,
                "action_type": action_type.strip()
            }
        )

        return approval

    def get_pending(self, thread_id=None, limit=20):
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 100
        ):
            raise ValueError("Limite inválido.")

        query = (
            self.client.table("odin_approvals")
            .select("*")
            .eq("status", "pending")
        )

        if thread_id is not None:
            if not isinstance(thread_id, str) or not thread_id.strip():
                raise ValueError("Thread ID inválido.")

            query = query.eq("thread_id", thread_id.strip())

        result = (
            query.order("requested_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    def decide(self, execution_id, decision, decision_by):
        try:
            UUID(execution_id)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ID da execução inválido.")

        if decision not in ("approved", "rejected"):
            raise ValueError("Decisão inválida.")

        if not isinstance(decision_by, str) or not decision_by.strip():
            raise ValueError(
                "Responsável pela decisão inválido."
            )

        decided_at = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("odin_approvals")
            .update({
                "status": decision,
                "decision_by": decision_by.strip(),
                "decided_at": decided_at
            })
            .eq("execution_id", execution_id)
            .eq("status", "pending")
            .select("*")
            .execute()
        )

        if not result.data:
            raise ValueError(
                "Solicitação inexistente ou já processada."
            )

        approval = result.data[0]

        event_type = (
            "approval_approved"
            if decision == "approved"
            else "approval_rejected"
        )

        self._record_audit(
            event_type=event_type,
            execution_id=execution_id,
            thread_id=approval.get("thread_id"),
            actor=decision_by.strip(),
            details={
                "decision": decision
            }
        )

        return approval

    def claim_approval(self, execution_id):
        """
        Reserva atomicamente uma aprovação concedida.

        Retorna o registro quando a reserva é realizada.
        Retorna None quando a aprovação não existe,
        não está aprovada ou já foi consumida.
        """

        try:
            UUID(execution_id)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ID da execução inválido.")

        result = (
            self.client
            .rpc(
                "odin_claim_approval",
                {
                    "p_execution_id": execution_id
                }
            )
            .execute()
        )

        if not result.data:
            return None

        approval = result.data[0]

        self._record_audit(
            event_type="approval_claimed",
            execution_id=execution_id,
            thread_id=approval.get("thread_id"),
            actor="ODIN",
            details={
                "step_id": approval.get("step_id"),
                "action_type": approval.get("action_type"),
                "status": "executing"
            }
        )

        return approval
