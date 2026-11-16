
from uuid import UUID

from supabase import create_client
from postgrest.exceptions import APIError

from app.config.settings import (
    get_supabase_url,
    get_supabase_key
)

from app.audit.audit_manager import AuditManager
from app.security.action_integrity import calculate_action_hash


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

    # ==========================================
    # SOLICITAÇÃO DE APROVAÇÃO
    # ==========================================

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
        description = description.strip()
        parameters = parameters or {}

        # Calcula a assinatura HMAC da ação.

        action_hash = calculate_action_hash(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        # Solicita aprovação ao Supabase.

        try:
            result = (
                self.client
                .rpc(
                    "odin_request_approval_v2",
                    {
                        "p_execution_id": execution_id,
                        "p_thread_id": thread_id,
                        "p_step_id": step_id,
                        "p_action_type": action_type,
                        "p_description": description,
                        "p_action_hash": action_hash,
                        "p_parameters": parameters
                    }
                )
                .execute()
            )

        except APIError as error:

            # PostgreSQL 23505:
            # violação de restrição UNIQUE.
            #
            # A duplicidade continua sendo bloqueada pelo banco.
            # Aqui apenas convertemos o erro para o formato
            # esperado pela aplicação.

            if getattr(error, "code", None) == "23505":
                raise RuntimeError(
                    "Já existe uma solicitação de aprovação "
                    "para esta execução."
                ) from error

            # Não esconder outros erros do Supabase.
            raise

        if not result.data:
            raise RuntimeError(
                "Não foi possível registrar a aprovação."
            )

        return result.data[0]

    # ==========================================
    # CONSULTA DE APROVAÇÕES PENDENTES
    # ==========================================

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

    # ==========================================
    # APROVAR OU REJEITAR SOLICITAÇÃO
    # ==========================================

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

    # ==========================================
    # REIVINDICAÇÃO SEGURA DA APROVAÇÃO
    # ==========================================

    def claim_approval(
        self,
        execution_id,
        thread_id,
        step_id,
        action_type,
        description,
        parameters=None
    ):
        """
        Reserva atomicamente uma aprovação concedida.

        Recalcula o HMAC da ação e envia os dados completos
        para validação pela função PostgreSQL.

        A mudança para executing e a auditoria acontecem
        na mesma transação do banco.
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

        if (
            not isinstance(description, str)
            or not description.strip()
        ):
            raise ValueError("Descrição inválida.")

        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("Parâmetros inválidos.")

        thread_id = thread_id.strip()
        action_type = action_type.strip()
        description = description.strip()
        parameters = parameters or {}

        # Recalcula a assinatura da ação.

        action_hash = calculate_action_hash(
            execution_id=execution_id,
            thread_id=thread_id,
            step_id=step_id,
            action_type=action_type,
            description=description,
            parameters=parameters
        )

        # Reivindica a aprovação atomicamente no banco.

        result = (
            self.client
            .rpc(
                "odin_claim_approval_v2",
                {
                    "p_execution_id": execution_id,
                    "p_thread_id": thread_id,
                    "p_step_id": step_id,
                    "p_action_type": action_type,
                    "p_description": description,
                    "p_parameters": parameters,
                    "p_action_hash": action_hash
                }
            )
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]
