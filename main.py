from app.agents.first_agent import run_agent


def show_help():
    print("""
========== JARVIS ODIN ==========

/planejar descrição da tarefa
    Cria um planejamento consultivo.
    Nenhuma ação externa será executada.

/ajuda
    Mostra esta lista de comandos.

sair
    Encerra o ODIN.

MODO: CONSULTIVO
Conversação, análise, organização e planejamento.
Execuções externas desativadas.

=================================
""")


def main():
    print("=" * 50)
    print("              JARVIS ODIN")
    print("       PERSONAL AI ASSISTANT")
    print("=" * 50)

    print("Assistente iniciado em modo consultivo.")
    print("Digite /ajuda para consultar os comandos.\n")

    while True:
        try:
            message = input("BRUNO: ").strip()

            if not message:
                continue

            if message.lower() in ["sair", "exit", "quit"]:
                print("\nODIN: Até logo. Encerrando sessão.")
                break

            if message.lower() == "/ajuda":
                show_help()
                continue

            if message.lower().startswith(
                ("/aprovar", "/rejeitar", "/pendentes")
            ):
                print(
                    "\nODIN: Administração de aprovações "
                    "desativada no modo consultivo.\n"
                )
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
