
from app.memory.supabase_memory import OdinMemory


def test_odin_memory():
    print("\nINICIANDO TESTE DO ODIN...")

    memory = OdinMemory()

    result = memory.save_memory(
        content="Meu nome é Bruno. Sou o criador do ODIN IA, meu JARVIS pessoal.",
        category="identity",
        importance=5
    )

    assert result, "ERRO: Não foi possível gravar a memória."

    print("MEMORIA GRAVADA COM SUCESSO!")

    memories = memory.search_memory(
        category="identity",
        limit=5
    )

    assert len(memories) > 0, "ERRO: Nenhuma memória recuperada."

    print("\nMEMORIA RECUPERADA:")
    print(memories[0]["content"])

    print("\nODIN MEMORY: TESTE CONCLUIDO!")


if __name__ == "__main__":
    test_odin_memory()
