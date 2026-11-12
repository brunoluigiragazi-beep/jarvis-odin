
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv

from app.memory.supabase_memory import OdinMemory

load_dotenv()

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


# Inicialização dos componentes
model = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3
)

odin_memory = OdinMemory()


def is_save_request(message: str) -> bool:
    """Identifica pedidos explícitos para guardar informações."""

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

    if any(term in text for term in ["não guarde", "não salve", "não registre"]):
        return False

    return any(trigger in text for trigger in triggers)


def get_memory_category(message: str) -> str:
    """Classifica a memória."""

    text = message.lower()

    if any(word in text for word in [
        "meu nome", "sou o criador", "minha função",
        "minha preferência"
    ]):
        return "identity"

    if any(word in text for word in [
        "projeto", "odin", "prioridade", "desenvolvimento"
    ]):
        return "project"

    return "general"


def get_persistent_memory() -> str:
    """Recupera memórias permanentes do Supabase."""

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


def process_message(state: MessagesState):
    """Processa mensagens com memória de curto e longo prazo."""

    latest_message = state["messages"][-1]
    user_message = latest_message.content

    save_status = ""

    # Grava somente quando Bruno solicitar explicitamente
    if isinstance(latest_message, HumanMessage):
        if isinstance(user_message, str) and is_save_request(user_message):

            try:
                odin_memory.save_memory(
                    content=user_message,
                    category=get_memory_category(user_message),
                    importance=5
                )

                save_status = (
                    "O pedido de gravação foi confirmado pelo Supabase. "
                    "Você pode informar ao Bruno que a memória foi salva."
                )

            except Exception as error:
                print(f"ERRO AO SALVAR MEMÓRIA: {error}")

                save_status = (
                    "A gravação da memória falhou. "
                    "Não informe ao Bruno que a informação foi salva."
                )

    # Recupera a memória permanente
    persistent_memory = get_persistent_memory()

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

    response = model.invoke(messages)

    return {"messages": [response]}


# Construção do grafo
builder = StateGraph(MessagesState)

builder.add_node("assistant", process_message)

builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

# Memória de curto prazo
memory = InMemorySaver()

graph = builder.compile(checkpointer=memory)


def run_agent(message: str, thread_id: str = "bruno"):
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return result["messages"][-1].content
