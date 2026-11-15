
from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from app.planning.planner import OdinPlanner
from app.executor.executor import OdinExecutor
from app.approvals.approval_manager import ApprovalManager


class OdinState(TypedDict, total=False):
    task: str
    context: str
    thread_id: str
    dry_run: bool
    plan: Any
    executions: list
    status: str
    error: str


class OdinOrchestrator:

    def __init__(
        self,
        planner=None,
        executor=None,
        approval_manager=None
    ):
        self.planner = planner or OdinPlanner()
        self.executor = executor or OdinExecutor()
        self.approval_manager = approval_manager

        self.graph = self._build_graph()

    def plan_task(self, state: OdinState):
        plan = self.planner.create_plan(
            task=state["task"],
            context=state.get("context", "")
        )

        return {"plan": plan}

    def execute_plan(self, state: OdinState):
        plan = state["plan"]
        dry_run = state.get("dry_run", True)
        thread_id = state.get("thread_id", "bruno")

        results = []

        for step in plan.steps:
            result = self.executor.execute(
                step=step,
                dry_run=dry_run,
                thread_id=thread_id
            )

            execution = result.model_dump(mode="json")

            if (
                execution["status"] == "waiting_approval"
                and self.approval_manager is not None
            ):
                approval = self.approval_manager.request_approval(
                    execution_id=execution["execution_id"],
                    thread_id=thread_id,
                    step_id=step.step_id,
                    action_type=step.action_type,
                    description=step.description,
                    parameters={
                        "expected_result": step.expected_result
                    }
                )

                if not isinstance(approval, dict):
                    raise RuntimeError(
                        "O Approval Manager não retornou "
                        "um registro de aprovação válido."
                    )

                execution["approval_id"] = approval["id"]
                execution["approval_status"] = approval["status"]

            results.append(execution)

        statuses = [item["status"] for item in results]

        if "blocked" in statuses:
            overall_status = "blocked"

        elif "waiting_approval" in statuses:
            overall_status = "waiting_approval"

        elif "dry_run" in statuses:
            overall_status = "simulated"

        else:
            overall_status = "completed"

        return {
            "executions": results,
            "status": overall_status
        }

    def resume_approved_step(
        self,
        step,
        execution_id,
        thread_id,
        dry_run=True
    ):
        """
        Retoma uma etapa somente após reivindicar uma
        aprovação válida no banco de dados.
        """

        if self.approval_manager is None:
            raise RuntimeError(
                "Approval Manager não configurado."
            )

        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("Thread ID inválido.")

        if not hasattr(step, "step_id"):
            raise ValueError("Etapa inválida.")

        if not hasattr(step, "action_type"):
            raise ValueError("Tipo de ação inválido.")

        authorization = self.approval_manager.claim_approval(
            execution_id=execution_id,
            thread_id=thread_id.strip(),
            step_id=step.step_id,
            action_type=step.action_type
        )

        if not isinstance(authorization, dict):
            return {
                "status": "waiting_approval",
                "executed": False,
                "message": (
                    "Nenhuma aprovação válida disponível "
                    "para esta execução."
                )
            }

        # Confere se o registro retornado pertence
        # exatamente à execução e à etapa solicitadas.

        valid_authorization = (
            str(authorization.get("execution_id")) == str(execution_id)
            and authorization.get("thread_id") == thread_id.strip()
            and authorization.get("step_id") == step.step_id
            and authorization.get("action_type") == step.action_type
            and authorization.get("status") == "executing"
        )

        if not valid_authorization:
            return {
                "status": "blocked",
                "executed": False,
                "message": (
                    "O registro de aprovação não corresponde "
                    "à execução solicitada."
                )
            }

        result = self.executor.execute(
            step=step,
            dry_run=dry_run,
            execution_id=execution_id,
            thread_id=thread_id.strip(),
            authorization=authorization
        )

        return result.model_dump(mode="json")

    def _build_graph(self):
        builder = StateGraph(OdinState)

        builder.add_node("planner", self.plan_task)
        builder.add_node("executor", self.execute_plan)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "executor")
        builder.add_edge("executor", END)

        return builder.compile()

    def run(
        self,
        task: str,
        context: str = "",
        dry_run: bool = True,
        thread_id: str = "bruno"
    ):
        if not isinstance(task, str) or not task.strip():
            raise ValueError("Tarefa inválida.")

        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("Thread ID inválido.")

        result = self.graph.invoke({
            "task": task.strip(),
            "context": context,
            "thread_id": thread_id.strip(),
            "dry_run": dry_run
        })

        plan = result["plan"]

        return {
            "status": result["status"],
            "plan": plan.model_dump(mode="json"),
            "executions": result["executions"]
        }
