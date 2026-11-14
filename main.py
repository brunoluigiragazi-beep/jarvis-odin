
from app.agents.first_agent import run_agent
from app.approvals.approval_manager import ApprovalManager
from app.security.pin_auth import authenticate


approval_manager = ApprovalManager()


def show_pending_approvals():
    try:
        pending = approval_manager.get_pending(limit=20)

        if not pending:
            print("\nODIN: Nenhuma aprovação pendente.\n")
            return

        print("\n========== APROVAÇÕES PENDENTES ==========\n")

        for item in pending:
            print(f"Execução: {item['execution_id']}")
            print(f"Etapa: {item['step_id']}")
            print(f"Ação: {item['action_type']}")
            print(f"Descrição: {item['description']}")
            print(f"Conversa: {item['thread_id']}")
            print(f"Solicitada em: {item['requested_at']}")
            print("-" * 45)

        print()

    except Exception as error:
        print(f"\nODIN: Erro ao consultar aprovações: {error}\n")


def decide_approval(command, execution_id):
    decisions = {
        "/aprovar": "approved",
        "/rejeitar": "rejected"
    }

    if command not in decisions:
        print("\nODIN: Comando de decisão inválido.\n")
        return

    decision = decisions[command]

    confirmation = input(
        f"\nConfirma {decision.upper()} esta solicitação? (s/n): "
    ).strip().lower()

    if confirmation != "s":
        print("\nODIN: Decisão cancelada.\n")
        return

    # Autenticação obrigatória antes de qualquer alteração no Supabase.
    print("\nODIN: Autenticação de segurança necessária.")

    try:
        authenticated = authenticate()

    except Exception as error:
        print(f"\nODIN: Falha na autenticação: {error}")
        print("Decisão bloqueada. Nenhuma alteração foi realizada.\n")
        return

    if not authenticated:
        print(
            "\nODIN: Decisão bloqueada. "
            "Nenhuma alteração foi realizada.\n"
        )
        return

    # Somente após autenticação o Supabase recebe a decisão.
    try:
        result = approval_manager.decide(
            execution_id=execution_id,
            decision=decision,
            decision_by="Bruno"
        )

        print("\nODIN: Decisão registrada no Supabase.")
        print(f"Execução: {result['execution_id']}")
        print(f"Status: {result['status']}")
        print("\nNenhuma ação externa foi executada.\n")

    except ValueError as error:
        print(f"\nODIN: {error}\n")

    except Exception as error:
        print(f"\nODIN: Erro ao registrar decisão: {error}\n")


def show_help():
    print("""
========== COMANDOS DO ODIN ==========

/pendentes
    Lista as aprovações aguardando decisão.

/aprovar UUID
    Aprova uma solicitação específica.

/rejeitar UUID
    Rejeita uma solicitação específica.

/ajuda
    Mostra esta lista de comandos.

sair
    Encerra o ODIN.

Para planejar uma tarefa:
/planejar descrição da tarefa

======================================
""")


def main():
    print("=" * 50)
    print("              ODIN AI")
    print("       PERSONAL AI ASSISTANT")
    print("=" * 50)

    print("Assistente iniciado.")
    print("Digite /ajuda para consultar os comandos.\n")

    while True:
        try:
            message = input("BRUNO: ").strip()

            if not message:
                continue

            if message.lower() in ["sair", "exit", "quit"]:
                print("\nODIN: Até logo. Encerrando sessão.")
                break

            parts = message.split(maxsplit=1)
            command = parts[0].lower()

            if command == "/ajuda":
                show_help()
                continue

            if command == "/pendentes":
                show_pending_approvals()
                continue

            if command in ["/aprovar", "/rejeitar"]:
                if len(parts) != 2:
                    print(
                        "\nODIN: Informe o UUID da execução.\n"
                        "Exemplo: /aprovar UUID\n"
                    )
                    continue

                execution_id = parts[1].strip()
                decide_approval(command, execution_id)
                continue

            response = run_agent(
                message,
                thread_id="bruno"
            )

            print(f"\nODIN: {response}\n")

        except KeyboardInterrupt:
            print("\n\nODIN: Sessão interrompida.")
            break

        except Exception as error:
            print(f"\nODIN: Ocorreu um erro: {error}\n")


if __name__ == "__main__":
    main()
