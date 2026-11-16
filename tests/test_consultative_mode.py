from types import SimpleNamespace

from app.executor.executor import OdinExecutor, ExecutionStatus


def test_consultative_executor_blocks_real_execution_even_with_authorization():
    executor = OdinExecutor()
    step = SimpleNamespace(
        step_id=1,
        action_type="read",
        description="Consultar um recurso"
    )

    result = executor.execute(
        step=step,
        dry_run=False,
        execution_id=None,
        thread_id="bruno",
        authorization={
            "status": "executing",
            "action_type": "read",
            "thread_id": "bruno",
            "step_id": 1
        }
    )

    assert result.status == ExecutionStatus.BLOCKED
    assert result.executed is False
    assert "Modo consultivo ativo" in result.message


def test_consultative_executor_keeps_plan_in_dry_run():
    executor = OdinExecutor()
    step = SimpleNamespace(
        step_id=1,
        action_type="analysis",
        description="Analisar arquitetura"
    )

    result = executor.execute(step=step, dry_run=True)

    assert result.status == ExecutionStatus.DRY_RUN
    assert result.executed is False
