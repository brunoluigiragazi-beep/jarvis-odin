from app.agents.first_agent import run_agent


def main():
    print("=" * 50)
    print("              ODIN AI")
    print("       PERSONAL AI ASSISTANT")
    print("=" * 50)
    print("Assistente iniciado. Digite 'sair' para encerrar.")
    print()

    while True:
        message = input("BRUNO: ").strip()

        if message.lower() in ["sair", "exit", "quit"]:
            print("\nODIN: Até logo. Estou encerrando nossa sessão.")
            break

        if not message:
            continue

        try:
            response = run_agent(message, thread_id="bruno")
            print(f"\nODIN: {response}\n")

        except Exception as error:
            print(f"\nODIN: Ocorreu um erro: {error}\n")


if __name__ == "__main__":
    main()
