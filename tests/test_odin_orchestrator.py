
from types import SimpleNamespace

from app.orchestration.orchestrator import OdinOrchestrator
from app.executor.executor import ExecutionStatus


class FakePlanner:

    def create_plan(self, task, context=""):
        return SimpleNamespace(
            title="Plano de teste",
            objective=task,
            steps=[
                SimpleNamespace(
                    step_id=1,
                    description="Analisar solicitação",
                    action_type="analysis",
                    expected_result="Análise concluída"
                ),
                SimpleNamespace(
                    step_id=2,
                    description="Excluir dados",
                    action_type="deletion",
                    expected_result="Aguardando autorização"
                )
            ],
            model_dump=lambda mode=None: {
                "title": "Plano de teste",
                "objective": task,
                "steps": []
            }
        )


def test_orchestrator_creates_and_processes_plan():
    orchestrator = OdinOrchestrator(planner=FakePlanner())

    result = orchestrator.run(
        task="Testar o ODIN",
        dry_run=True
    )

    assert result["status"] == "waiting_approval"
    assert len(result["executions"]) == 2


def test_orchestrator_waits_for_sensitive_action():
    orchestrator = OdinOrchestrator(planner=FakePlanner())

    result = orchestrator.run(
        task="Testar autorização"
    )

    assert (
        result["executions"][1]["status"]
        == ExecutionStatus.WAITING_APPROVAL.value
    )


def test_orchestrator_rejects_empty_task():
    orchestrator = OdinOrchestrator(planner=FakePlanner())

    try:
        orchestrator.run("")
        assert False, "Deveria rejeitar tarefa vazia."

    except ValueError:
        assert True
