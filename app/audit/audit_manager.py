
from uuid import UUID

from supabase import create_client

from app.config.settings import (
    get_supabase_url,
    get_supabase_key,
)


class AuditManager:

    def __init__(self):
        self.client = create_client(
            get_supabase_url(),
            get_supabase_key()
        )

    def log_event(
        self,
        event_type,
        execution_id=None,
        thread_id=None,
        actor="ODIN",
        details=None
    ):
        # Validar tipo de evento
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("Tipo de evento inválido.")

        # Validar responsável
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("Responsável pelo evento inválido.")

        # Validar ID da execução, quando informado
        if execution_id is not None:
            try:
                UUID(execution_id)
            except (ValueError, TypeError, AttributeError):
                raise ValueError("ID da execução inválido.")

        # Validar thread
        if thread_id is not None:
            if not isinstance(thread_id, str) or not thread_id.strip():
                raise ValueError("Thread ID inválido.")

        # Validar detalhes
        if details is not None and not isinstance(details, dict):
            raise ValueError("Detalhes do evento devem ser um dicionário.")

        payload = {
            "event_type": event_type.strip(),
            "execution_id": execution_id,
            "thread_id": thread_id.strip() if thread_id else None,
            "actor": actor.strip(),
            "details": details or {},
        }

        result = (
            self.client
            .table("odin_audit_logs")
            .insert(payload)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Não foi possível registrar o evento de auditoria."
            )

        return result.data[0]
