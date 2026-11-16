
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.security.policy import OdinPolicy, Decision


class ExecutionStatus(str, Enum):
    DRY_RUN = "dry_run"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    EXECUTED = "executed"


class ExecutionResult(BaseModel):
    execution_id: str
    action_type: str
    status: ExecutionStatus
    message: str
    executed: bool = False


class OdinExecutor:

    def __init__(self):
        self.policy = OdinPolicy()

    @staticmethod
    def _validate_execution_id(execution_id):
        try:
            return str(UUID(str(execution_id)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ID da execução inválido.")

    @staticmethod
    def _validate_authorization(
        authorization,
        execution_id,
        thread_id,
        step
    ):
        if not isinstance(authorization, dict):
            return False

        return (
            authorization.get("execution_id") == execution_id
            and authorization.get("thread_id") == thread_id
            and authorization.get("step_id") == step.step_id
            and authorization.get("action_type") == step.action_type
            and authorization.get("status") == "executing"
        )

    def execute(
        self,
        step,
        dry_run=True,
        execution_id=None,
        thread_id=None,
        authorization=None
    ):

        if execution_id is None:
            execution_id = str(uuid4())
        else:
            execution_id = self._validate_execution_id(
                execution_id
            )

        action_type = step.action_type

        permission = self.policy.evaluate(action_type)

        # Fail-closed: esta versão do ODIN opera exclusivamente em
        # modo consultivo. Nenhuma autorização habilita execução real.
        if not dry_run:
            return ExecutionResult(
                execution_id=execution_id,
                action_type=permission.action_type,
                status=ExecutionStatus.BLOCKED,
                message=(
                    "Modo consultivo ativo. Execução externa bloqueada; "
                    "nenhuma ferramenta foi chamada."
                ),
                executed=False
            )

        if permission.decision == Decision.BLOCKED:
            return ExecutionResult(
                execution_id=execution_id,
                action_type=permission.action_type,
                status=ExecutionStatus.BLOCKED,
                message=permission.reason
            )

        if permission.requires_approval:
            valid_authorization = self._validate_authorization(
                authorization=authorization,
                execution_id=execution_id,
                thread_id=thread_id,
                step=step
            )

            if not valid_authorization:
                return ExecutionResult(
                    execution_id=execution_id,
                    action_type=permission.action_type,
                    status=ExecutionStatus.WAITING_APPROVAL,
                    message=(
                        "Ação aguardando autorização válida "
                        "e vinculada à execução."
                    )
                )

        if dry_run:
            return ExecutionResult(
                execution_id=execution_id,
                action_type=permission.action_type,
                status=ExecutionStatus.DRY_RUN,
                message=(
                    "Autorização validada para simulação. "
                    "Nenhuma operação real foi executada."
                )
            )

        return ExecutionResult(
            execution_id=execution_id,
            action_type=permission.action_type,
            status=ExecutionStatus.BLOCKED,
            message=(
                "Execução real bloqueada. "
                "Nenhuma ferramenta de execução foi registrada."
            )
        )
