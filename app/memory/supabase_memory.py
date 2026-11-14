
from supabase import create_client

from app.config.settings import (
    get_supabase_url,
    get_supabase_key
)


class OdinMemory:

    def __init__(self):
        self.client = create_client(
            get_supabase_url(),
            get_supabase_key()
        )

    # ==========================================
    # MEMORIA PERMANENTE
    # ==========================================

    def save_memory(
        self,
        content,
        category="general",
        importance=3
    ):
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Conteúdo vazio.")

        if not isinstance(importance, int) or not 1 <= importance <= 5:
            raise ValueError(
                "Importância deve estar entre 1 e 5."
            )

        result = self.client.table("odin_memory").insert({
            "content": content,
            "category": category,
            "importance": importance,
            "source": "jarvis",
            "is_active": True
        }).execute()

        return result.data

    def search_memory(self, category=None, limit=10):

        if limit < 1:
            raise ValueError("Limite inválido.")

        query = (
            self.client.table("odin_memory")
            .select("*")
            .eq("is_active", True)
        )

        if category:
            query = query.eq("category", category)

        return (
            query.order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )

    # ==========================================
    # GERENCIAMENTO DE CONVERSAS
    # ==========================================

    def get_or_create_conversation(
        self,
        thread_id,
        title=None
    ):

        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("Thread ID inválido.")

        existing = (
            self.client.table("odin_conversations")
            .select("id")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            return existing.data[0]["id"]

        conversation = {
            "thread_id": thread_id,
            "status": "active"
        }

        if title:
            conversation["title"] = title[:200]

        result = (
            self.client.table("odin_conversations")
            .insert(conversation)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Não foi possível criar a conversa."
            )

        return result.data[0]["id"]

    def get_conversation(self, thread_id):

        result = (
            self.client.table("odin_conversations")
            .select("*")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    # ==========================================
    # REGISTRO DE MENSAGENS
    # ==========================================

    def save_message(
        self,
        thread_id,
        role,
        content,
        metadata=None
    ):

        if role not in ("user", "assistant"):
            raise ValueError("Papel da mensagem inválido.")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Mensagem vazia.")

        conversation_id = self.get_or_create_conversation(
            thread_id=thread_id,
            title=content[:100] if role == "user" else None
        )

        result = (
            self.client.table("odin_messages")
            .insert({
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {}
            })
            .execute()
        )

        return result.data

    # ==========================================
    # RECUPERACAO DO HISTORICO
    # ==========================================

    def get_messages(self, thread_id, limit=30):

        if limit < 1:
            raise ValueError("Limite inválido.")

        conversation = self.get_conversation(thread_id)

        if not conversation:
            return []

        result = (
            self.client.table("odin_messages")
            .select("*")
            .eq("conversation_id", conversation["id"])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return list(reversed(result.data or []))
