
from uuid import uuid4

from app.memory.supabase_memory import OdinMemory


def test_odin_conversations():

    print("\nINICIANDO TESTE DE CONVERSAS ODIN...")

    memory = OdinMemory()

    # Identificador exclusivo para este teste
    thread_id = f"teste_{uuid4().hex[:12]}"

    # 1. Criar conversa
    conversation_id = memory.get_or_create_conversation(
        thread_id=thread_id,
        title="Teste de memória ODIN"
    )

    assert conversation_id, "ERRO: Conversa não criada."

    print("1. CONVERSA CRIADA COM SUCESSO!")

    # 2. Salvar mensagem do Bruno
    memory.save_message(
        thread_id=thread_id,
        role="user",
        content="Olá ODIN, vamos testar sua memória."
    )

    print("2. MENSAGEM DO BRUNO REGISTRADA!")

    # 3. Salvar resposta do ODIN
    memory.save_message(
        thread_id=thread_id,
        role="assistant",
        content="Olá Bruno! Estou registrando nossa conversa."
    )

    print("3. RESPOSTA DO ODIN REGISTRADA!")

    # 4. Recuperar histórico
    messages = memory.get_messages(
        thread_id=thread_id,
        limit=10
    )

    assert len(messages) == 2, (
        f"ERRO: Esperadas 2 mensagens, encontradas {len(messages)}."
    )

    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    print("4. HISTÓRICO RECUPERADO COM SUCESSO!")

    # 5. Conferir conteúdo
    for message in messages:
        print(f'{message["role"].upper()}: {message["content"]}')

    print("\nODIN CONVERSATIONS: TESTE CONCLUÍDO!")


if __name__ == "__main__":
    test_odin_conversations()
