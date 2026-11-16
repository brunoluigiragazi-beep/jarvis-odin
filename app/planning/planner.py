
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator
from langchain_openai import ChatOpenAI

from app.config.settings import get_model_name


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


class SecureModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )


class PlanStep(SecureModel):
    step_id: int = Field(ge=1, description="Número sequencial da etapa")

    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Descrição objetiva da tarefa"
    )

    action_type: ActionType = Field(
        description="Categoria da ação"
    )

    expected_result: str = Field(
        min_length=1,
        max_length=2000,
        description="Resultado esperado da etapa"
    )

    @field_validator("step_id", mode="before")
    @classmethod
    def validate_step_id(cls, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("step_id deve ser um número inteiro.")
        return value

    @field_validator("description", "expected_result")
    @classmethod
    def validate_text(cls, value):
        if not value or not value.strip():
            raise ValueError("O campo não pode estar vazio.")
        return value


class ExecutionPlan(SecureModel):
    title: str = Field(min_length=1, max_length=200)

    objective: str = Field(min_length=1, max_length=2000)

    steps: list[PlanStep] = Field(
        min_length=1,
        max_length=8
    )

    @field_validator("title", "objective")
    @classmethod
    def validate_plan_text(cls, value):
        if not value or not value.strip():
            raise ValueError("O campo não pode estar vazio.")
        return value

    @field_validator("steps")
    @classmethod
    def validate_step_sequence(cls, steps):
        step_ids = [step.step_id for step in steps]

        if step_ids != list(range(1, len(steps) + 1)):
            raise ValueError(
                "As etapas devem possuir IDs sequenciais começando em 1."
            )

        return steps


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

        if not isinstance(context, str):
            raise ValueError("Contexto inválido.")

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

OBJETIVO:
{task}

CONTEXTO DISPONÍVEL:
{context}

Produza um plano estruturado.
"""

        return self.planner.invoke(prompt)
