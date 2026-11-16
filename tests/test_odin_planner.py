
import pytest
from pydantic import ValidationError

from app.planning.planner import PlanStep, ExecutionPlan


def test_valid_plan_step():
    step = PlanStep(
        step_id=1,
        description="Analisar os dados",
        action_type="analysis",
        expected_result="Relatório de análise"
    )

    assert step.step_id == 1
    assert step.action_type == "analysis"


def test_rejects_invalid_step_id():
    with pytest.raises(ValidationError):
        PlanStep(
            step_id=0,
            description="Analisar dados",
            action_type="analysis",
            expected_result="Relatório"
        )


def test_rejects_unknown_action_type():
    with pytest.raises(ValidationError):
        PlanStep(
            step_id=1,
            description="Executar tarefa",
            action_type="unknown",
            expected_result="Resultado"
        )


def test_rejects_empty_description():
    with pytest.raises(ValidationError):
        PlanStep(
            step_id=1,
            description="   ",
            action_type="analysis",
            expected_result="Resultado"
        )


def test_rejects_empty_expected_result():
    with pytest.raises(ValidationError):
        PlanStep(
            step_id=1,
            description="Analisar dados",
            action_type="analysis",
            expected_result=""
        )


def test_rejects_extra_fields():
    with pytest.raises(ValidationError):
        PlanStep(
            step_id=1,
            description="Analisar dados",
            action_type="analysis",
            expected_result="Relatório",
            unauthorized_field="unexpected"
        )


def test_execution_plan_requires_steps():
    with pytest.raises(ValidationError):
        ExecutionPlan(
            title="Plano de análise",
            objective="Analisar dados",
            steps=[]
        )
