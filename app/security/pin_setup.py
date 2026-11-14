
import hashlib
import secrets
import msvcrt
import sys
from pathlib import Path

ITERATIONS = 600_000
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def read_pin(prompt):
    print(prompt, end="", flush=True)
    pin = ""

    while True:
        char = msvcrt.getwch()

        if char in ("\r", "\n"):
            print()
            return pin

        if char == "\x03":
            raise KeyboardInterrupt

        if char in ("\b", "\x7f"):
            if pin:
                pin = pin[:-1]
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue

        if char.isdigit() and len(pin) < 8:
            pin += char
            sys.stdout.write("*")
            sys.stdout.flush()


def generate_pin_hash(pin):
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        ITERATIONS
    )

    return (
        f"pbkdf2_sha256${ITERATIONS}"
        f"${salt.hex()}${derived_key.hex()}"
    )


def save_hash_to_env(pin_hash):
    key = "ODIN_APPROVAL_PIN_HASH"
    lines = []

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    new_line = f'{key}="{pin_hash}"'
    result = []
    updated = False

    for line in lines:
        if line.strip().startswith(f"{key}="):
            if not updated:
                result.append(new_line)
                updated = True
        else:
            result.append(line)

    if not updated:
        result.append(new_line)

    ENV_FILE.write_text(
        "\n".join(result) + "\n",
        encoding="utf-8"
    )


def main():
    print("=============================================")
    print("       ODIN - CONFIGURAÇÃO DE PIN")
    print("=============================================")

    pin = read_pin("Crie seu PIN (8 dígitos): ")
    confirmation = read_pin("Confirme seu PIN: ")

    if len(pin) != 8:
        print("Erro: o PIN deve ter exatamente 8 dígitos.")
        return

    if pin != confirmation:
        print("Erro: os PINs não correspondem.")
        return

    pin_hash = generate_pin_hash(pin)
    save_hash_to_env(pin_hash)

    print("\nPIN configurado com sucesso.")
    print("Hash salvo automaticamente no arquivo .env.")
    print("O valor secreto não será exibido.")


if __name__ == "__main__":
    main()
