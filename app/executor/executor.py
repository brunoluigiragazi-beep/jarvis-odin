
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel

from app.security.policy import OdinPolicy, Decision


# ==========================================
# ESTADOS DE EXECUÇÃO
# ==========================================

class ExecutionStatus(str, Enum):
    DRY_RUN = "dry_run"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    EXECUTED = "executed"


# ==========================================
# RESULTADO
# ==========================================

class ExecutionResult(BaseModel):
    execution_id: str
    action_type: str
    status: ExecutionStatus
    message: str
    executed: bool = False


# ==========================================
# ODIN EXECUTOR
# ==========================================

class OdinExecutor:

    def __init__(self):
        self.policy = OdinPolicy()

    def execute(
        self,
        step,
        dry_run=True,
        approved=False
    ) -> ExecutionResult:

        action_type = step.action_type
        execution_id = str(uuid4())

        # 1. Verificar política de segurança
        permission = self.policy.evaluate(action_type)

        # 2. Bloquear ações desconhecidas
        if permission.decision == Decision.BLOCKED:

            return ExecutionResult(
                execution_id=execution_id,
                action_type=action_type,
                status=ExecutionStatus.BLOCKED,
                message=permission.reason
            )

        # 3. Exigir aprovação explícita
        if permission.requires_approval and not approved:

            return ExecutionResult(
                execution_id=execution_id,
                action_type=action_type,
                status=ExecutionStatus.WAITING_APPROVAL,
                message=(
                    "Ação aguardando autorização explícita de Bruno."
                )
            )

        # 4. Modo de simulação
        if dry_run:

            return ExecutionResult(
                execution_id=execution_id,
                action_type=action_type,
                status=ExecutionStatus.DRY_RUN,
                message=(
                    "Ação autorizada para simulação. "
                    "Nenhuma operação real foi executada."
                )
            )

        # 5. Bloquear execução real sem ferramenta registrada
        return ExecutionResult(
            execution_id=execution_id,
            action_type=action_type,
            status=ExecutionStatus.BLOCKED,
            message=(
                "Nenhuma ferramenta de execução real "
                "foi registrada para esta ação."
            )
        )
