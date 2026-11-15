
from types import SimpleNamespace

from app.orchestration.orchestrator import OdinOrchestrator
from app.executor.executor import ExecutionStatus


EXECUTION_ID = "12345678-1234-5678-1234-567812345678"
THREAD_ID = "thread-test-001"


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


class FakeApprovalManager:

    def __init__(self, authorization=None):
        self.authorization = authorization
        self.claim_calls = []

    def claim_approval(
        self,
        execution_id,
        thread_id,
        step_id,
        action_type
    ):
        self.claim_calls.append({
            "execution_id": execution_id,
            "thread_id": thread_id,
            "step_id": step_id,
            "action_type": action_type
        })

        return self.authorization


def make_deletion_step():
    return SimpleNamespace(
        step_id=2,
        description="Excluir dados",
        action_type="deletion",
        expected_result="Dados excluídos"
    )


def make_authorization(
    execution_id=EXECUTION_ID,
    thread_id=THREAD_ID,
    step_id=2,
    action_type="deletion",
    status="executing"
):
    return {
        "execution_id": execution_id,
        "thread_id": thread_id,
        "step_id": step_id,
        "action_type": action_type,
        "status": status
    }


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


def test_resume_with_valid_approval_runs_dry_run():
    approval_manager = FakeApprovalManager(
        authorization=make_authorization()
    )

    orchestrator = OdinOrchestrator(
        approval_manager=approval_manager
    )

    result = orchestrator.resume_approved_step(
        step=make_deletion_step(),
        execution_id=EXECUTION_ID,
        thread_id=THREAD_ID,
        dry_run=True
    )

    assert result["status"] == ExecutionStatus.DRY_RUN.value
    assert result["executed"] is False
    assert len(approval_manager.claim_calls) == 1


def test_resume_without_approval_remains_waiting():
    approval_manager = FakeApprovalManager(
        authorization=None
    )

    orchestrator = OdinOrchestrator(
        approval_manager=approval_manager
    )

    result = orchestrator.resume_approved_step(
        step=make_deletion_step(),
        execution_id=EXECUTION_ID,
        thread_id=THREAD_ID
    )

    assert result["status"] == "waiting_approval"
    assert result["executed"] is False


def test_resume_with_mismatched_approval_is_blocked():
    approval_manager = FakeApprovalManager(
        authorization=make_authorization(
            thread_id="another-thread"
        )
    )

    orchestrator = OdinOrchestrator(
        approval_manager=approval_manager
    )

    result = orchestrator.resume_approved_step(
        step=make_deletion_step(),
        execution_id=EXECUTION_ID,
        thread_id=THREAD_ID
    )

    assert result["status"] == "blocked"
    assert result["executed"] is False


def test_resume_never_executes_real_action():
    approval_manager = FakeApprovalManager(
        authorization=make_authorization()
    )

    orchestrator = OdinOrchestrator(
        approval_manager=approval_manager
    )

    result = orchestrator.resume_approved_step(
        step=make_deletion_step(),
        execution_id=EXECUTION_ID,
        thread_id=THREAD_ID,
        dry_run=False
    )

    assert result["status"] == ExecutionStatus.BLOCKED.value
    assert result["executed"] is False
