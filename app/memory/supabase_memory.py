
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)


class OdinMemory:

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("Credenciais Supabase não configuradas.")

        self.client = create_client(url, key)

    def save_memory(self, content, category="general", importance=3):
        if not content.strip():
            raise ValueError("Conteúdo vazio.")

        if not 1 <= importance <= 5:
            raise ValueError("Importância deve estar entre 1 e 5.")

        result = self.client.table("odin_memory").insert({
            "content": content,
            "category": category,
            "importance": importance,
            "source": "jarvis",
            "is_active": True
        }).execute()

        return result.data

    def search_memory(self, category=None, limit=10):
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
