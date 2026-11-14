
from typing import Literal

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.config.settings import get_model_name


# ==========================================
# ESTRUTURA DO PLANO
# ==========================================

ActionType = Literal[
    "analysis",
    "read",
    "write",
    "communication",
    "deletion",
    "financial",
    "configuration",
    "other"
]


class PlanStep(BaseModel):
    step_id: int = Field(description="Número sequencial da etapa")

    description: str = Field(
        description="Descrição objetiva da tarefa"
    )

    action_type: ActionType = Field(
        description="Categoria da ação"
    )

    expected_result: str = Field(
        description="Resultado esperado da etapa"
    )


class ExecutionPlan(BaseModel):
    title: str = Field(
        description="Título do plano"
    )

    objective: str = Field(
        description="Objetivo principal solicitado por Bruno"
    )

    steps: list[PlanStep] = Field(
        min_length=1,
        max_length=8,
        description="Etapas necessárias para atingir o objetivo"
    )


# ==========================================
# ODIN PLANNER
# ==========================================

class OdinPlanner:

    def __init__(self):

        self.model = ChatOpenAI(
            model=get_model_name(),
            temperature=0
        )

        self.planner = self.model.with_structured_output(
            ExecutionPlan
        )

    def create_plan(
        self,
        task: str,
        context: str = ""
    ) -> ExecutionPlan:

        if not isinstance(task, str) or not task.strip():
            raise ValueError("Tarefa inválida.")

        prompt = f"""
Você é o ODIN PLANNER.

Sua responsabilidade é transformar objetivos em planos
de execução organizados e objetivos.

REGRAS:

1. Divida o objetivo em etapas sequenciais.
2. Cada etapa deve ter uma finalidade clara.
3. Não execute nenhuma ação.
4. Não afirme que uma tarefa foi concluída.
5. Identifique corretamente o tipo de cada ação.
6. Não invente informações ausentes.
7. Se faltar informação essencial, indique isso
   claramente na descrição da etapa.
8. Nunca classifique exclusões, operações financeiras
   ou comunicações externas como simples consultas.

OBJETIVO DE BRUNO:
{task}

CONTEXTO DISPONÍVEL:
{context}

Produza um plano estruturado.
"""

        result = self.planner.invoke(prompt)

        return result
