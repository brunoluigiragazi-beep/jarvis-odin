
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
            execution_id = str(UUID(execution_id))
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

        thread_id = thread_id.strip()
        action_type = action_type.strip()

        existing = (
            self.client
            .table("odin_approvals")
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
            self.client
            .table("odin_approvals")
            .insert({
                "execution_id": execution_id,
                "thread_id": thread_id,
                "step_id": step_id,
                "action_type": action_type,
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
            thread_id=thread_id,
            actor="ODIN",
            details={
                "step_id": step_id,
                "action_type": action_type
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
            self.client
            .table("odin_approvals")
            .select("*")
            .eq("status", "pending")
        )

        if thread_id is not None:

            if not isinstance(thread_id, str) or not thread_id.strip():
                raise ValueError("Thread ID inválido.")

            query = query.eq("thread_id", thread_id.strip())

        result = (
            query
            .order("requested_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    def decide(
        self,
        execution_id,
        decision,
        decision_by
    ):
        """
        Aprova ou rejeita uma solicitação.

        A atualização do status e o registro da auditoria
        são executados atomicamente pela função PostgreSQL
        odin_decide_approval_v2.
        """

        try:
            execution_id = str(UUID(str(execution_id)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(
                "ID da execução inválido."
            )

        if decision not in ("approved", "rejected"):
            raise ValueError("Decisão inválida.")

        if (
            not isinstance(decision_by, str)
            or not decision_by.strip()
        ):
            raise ValueError(
                "Responsável pela decisão inválido."
            )

        result = (
            self.client
            .rpc(
                "odin_decide_approval_v2",
                {
                    "p_execution_id": execution_id,
                    "p_decision": decision,
                    "p_decision_by": decision_by.strip()
                }
            )
            .execute()
        )

        if not result.data:
            raise ValueError(
                "Solicitação inexistente ou já processada."
            )

        return result.data[0]

    def claim_approval(
        self,
        execution_id,
        thread_id,
        step_id,
        action_type
    ):
        """
        Reserva atomicamente uma aprovação concedida.

        A função PostgreSQL odin_claim_approval_v2 valida
        os identificadores, atualiza o status para executing
        e registra o evento de auditoria na mesma transação.
        """

        try:
            execution_id = str(UUID(str(execution_id)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(
                "ID da execução inválido."
            )

        if (
            not isinstance(thread_id, str)
            or not thread_id.strip()
        ):
            raise ValueError("Thread ID inválido.")

        if (
            not isinstance(step_id, int)
            or isinstance(step_id, bool)
            or step_id < 1
        ):
            raise ValueError("ID da etapa inválido.")

        if (
            not isinstance(action_type, str)
            or not action_type.strip()
        ):
            raise ValueError("Tipo de ação inválido.")

        result = (
            self.client
            .rpc(
                "odin_claim_approval_v2",
                {
                    "p_execution_id": execution_id,
                    "p_thread_id": thread_id.strip(),
                    "p_step_id": step_id,
                    "p_action_type": action_type.strip()
                }
            )
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]
