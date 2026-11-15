
from enum import Enum
from pydantic import BaseModel


class Decision(str, Enum):
    AUTO = "auto"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class PolicyResult(BaseModel):
    action_type: str
    decision: Decision
    requires_approval: bool
    reason: str


class OdinPolicy:

    AUTO_ACTIONS = {
        "analysis",
        "read"
    }

    APPROVAL_ACTIONS = {
        "write",
        "communication",
        "deletion",
        "financial",
        "configuration",
        "other"
    }

    def evaluate(self, action_type: str) -> PolicyResult:

        if not isinstance(action_type, str):
            action_type = ""

        action_type = action_type.strip().lower()

        if action_type in self.AUTO_ACTIONS:
            return PolicyResult(
                action_type=action_type,
                decision=Decision.AUTO,
                requires_approval=False,
                reason="Ação permitida pela política automática."
            )

        if action_type in self.APPROVAL_ACTIONS:
            return PolicyResult(
                action_type=action_type,
                decision=Decision.APPROVAL_REQUIRED,
                requires_approval=True,
                reason="Ação exige autorização humana explícita."
            )

        return PolicyResult(
            action_type=action_type or "unknown",
            decision=Decision.BLOCKED,
            requires_approval=True,
            reason="Tipo de ação desconhecido. Execução bloqueada."
        )
