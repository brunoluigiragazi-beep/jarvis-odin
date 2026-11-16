
import os
from dotenv import load_dotenv

load_dotenv(override=False)


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value or not value.strip():
        raise RuntimeError(
            f"Configuração obrigatória ausente: {name}"
        )

    return value.strip()


def get_openai_api_key() -> str:
    return get_required_env("OPENAI_API_KEY")


def get_supabase_url() -> str:
    return get_required_env("SUPABASE_URL")


def get_supabase_key() -> str:
    return get_required_env("SUPABASE_KEY")


def get_model_name() -> str:
    return os.getenv(
        "ODIN_MODEL",
        "gpt-4.1-mini"
    ).strip()
def get_action_integrity_key() -> str:
    return get_required_env("ODIN_ACTION_INTEGRITY_KEY")