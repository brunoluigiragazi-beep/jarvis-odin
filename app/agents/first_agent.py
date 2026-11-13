
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END, MessagesState
from dotenv import load_dotenv

from app.memory.supabase_memory import OdinMemory

load_dotenv(override=True)


# ==========================================
# IDENTIDADE DO ODIN
# ==========================================

SYSTEM_PROMPT = """
Você é ODIN, o assistente pessoal JARVIS de Bruno.

IDENTIDADE:
- Seu criador e usuário principal é Bruno.
- Você é o ODIN IA, seu assistente pessoal e parceiro técnico.
- Seu propósito é auxiliar Bruno na organização e execução de projetos.

PERSONALIDADE:
- Profissional, inteligente e elegante.
- Comunicação natural, cordial e objetiva.
- Português brasileiro.
- Identidade conceitualmente masculina.
- Seja proativo sem ser invasivo.

CAPACIDADES:
- Python, LangGraph, RAG e Supabase.
- Desenvolvimento de agentes inteligentes.
- Automação, APIs e integrações.
- Organização e gerenciamento de projetos.

REGRAS:
- Consulte as memórias fornecidas antes de responder.
- Considere o histórico da conversa.
- Não invente informações.
- Nunca afirme que executou uma ação sem executá-la.
- Solicite autorização antes de ações sensíveis.
- Não afirme que salvou uma memória se o sistema não confirmou a gravação.
"""


# ==========================================
# INICIALIZAÇÃO
# ==========================================

model = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3
)

odin_memory = OdinMemory()


# ==========================================
# IDENTIFICAÇÃO DE PEDIDOS DE MEMÓRIA
# ==========================================

def is_save_request(message: str) -> bool:

    triggers = [
        "guarde que",
        "guarde essa informação",
        "lembre que",
        "lembre-se que",
        "anote que",
        "registre que",
        "salve na memória",
        "não esqueça que"
    ]

    text = message.lower()

    if any(term in text for term in [
        "não guarde",
        "não salve",
        "não registre"
    ]):
        return False

    return any(trigger in text for trigger in triggers)


def get_memory_category(message: str) -> str:

    text = message.lower()

    if any(word in text for word in [
        "meu nome",
        "sou o criador",
        "minha função",
        "minha preferência"
    ]):
        return "identity"

    if any(word in text for word in [
        "projeto",
        "odin",
        "prioridade",
        "desenvolvimento"
    ]):
        return "project"

    return "general"


# ==========================================
# RECUPERAÇÃO DA MEMÓRIA PERMANENTE
# ==========================================

def get_persistent_memory() -> str:

    try:
        memories = odin_memory.search_memory(limit=10)

        if not memories:
            return "Nenhuma memória permanente encontrada."

        context = []

        for item in memories:

            category = item.get("category", "general")
            content = item.get("content", "")

            if content:
                context.append(
                    f"[{category}] {content}"
                )

        return "\n".join(context)

    except Exception as error:

        print(f"AVISO: Erro ao consultar memória: {error}")

        return "Memória permanente temporariamente indisponível."


# ==========================================
# PROCESSAMENTO PRINCIPAL
# ==========================================

def process_message(
    state: MessagesState,
    config: RunnableConfig
):
    """Processa e registra cada interação do ODIN."""

    latest_message = state["messages"][-1]

    if not isinstance(latest_message, HumanMessage):
        raise ValueError(
            "A última mensagem precisa ser uma mensagem do usuário."
        )

    user_message = latest_message.content

    if not isinstance(user_message, str):
        raise ValueError("Mensagem do usuário inválida.")

    thread_id = config["configurable"]["thread_id"]

    # 1. Registra a mensagem do Bruno
    odin_memory.save_message(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    print("ODIN: Mensagem do Bruno registrada.")

    # 2. Identifica pedidos de gravação permanente
    save_status = ""

    if is_save_request(user_message):

        try:

            odin_memory.save_memory(
                content=user_message,
                category=get_memory_category(user_message),
                importance=5
            )

            save_status = (
                "A gravação permanente foi confirmada. "
                "Você pode informar ao Bruno que a memória foi salva."
            )

        except Exception as error:

            print(f"ERRO AO SALVAR MEMÓRIA: {error}")

            save_status = (
                "A gravação permanente falhou. "
                "Não informe que a memória foi salva."
            )

    # 3. Recupera memórias permanentes
    persistent_memory = get_persistent_memory()

    # 4. Monta contexto do agente
    system_context = f"""
{SYSTEM_PROMPT}

MEMÓRIA PERMANENTE DO BRUNO:
{persistent_memory}

STATUS DA GRAVAÇÃO:
{save_status if save_status else "Nenhum pedido de gravação nesta mensagem."}

Utilize as informações acima quando forem relevantes.
Não invente memórias nem confunda informações antigas com atuais.
"""

    messages = [
        SystemMessage(content=system_context),
        *state["messages"]
    ]

    # 5. Executa o modelo
    response = model.invoke(messages)

    # 6. Registra a resposta do ODIN
    odin_memory.save_message(
        thread_id=thread_id,
        role="assistant",
        content=response.content
    )

    print("ODIN: Resposta registrada no Supabase.")

    return {
        "messages": [response]
    }


# ==========================================
# CONSTRUÇÃO DO LANGGRAPH
# ==========================================

builder = StateGraph(MessagesState)

builder.add_node("assistant", process_message)

builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

# O histórico será recuperado diretamente do Supabase.
# Não utilizamos checkpoint temporário neste fluxo.

graph = builder.compile()


# ==========================================
# RECUPERAÇÃO DO HISTÓRICO
# ==========================================

def load_conversation_history(thread_id: str):

    records = odin_memory.get_messages(
        thread_id=thread_id,
        limit=30
    )

    history = []

    for item in records:

        role = item.get("role")
        content = item.get("content", "")

        if not content:
            continue

        if role == "user":

            history.append(
                HumanMessage(content=content)
            )

        elif role == "assistant":

            history.append(
                AIMessage(content=content)
            )

    return history


# ==========================================
# EXECUÇÃO DO AGENTE
# ==========================================

def run_agent(
    message: str,
    thread_id: str = "bruno"
):

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Mensagem inválida ou vazia.")

    # Recupera o histórico persistente
    history = load_conversation_history(thread_id)

    # Adiciona a nova mensagem
    history.append(
        HumanMessage(content=message.strip())
    )

    # Executa o grafo
    result = graph.invoke(
        {
            "messages": history
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return result["messages"][-1].content
