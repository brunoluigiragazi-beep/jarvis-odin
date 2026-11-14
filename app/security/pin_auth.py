
import hashlib
import hmac
import msvcrt
import sys
import sqlite3
import time

from pathlib import Path

from app.config.settings import get_required_env
from app.audit.audit_manager import AuditManager


# Configurações de segurança
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

# Banco local de segurança
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECURITY_DIR = PROJECT_ROOT / "data"
SECURITY_DB = SECURITY_DIR / "odin_security.db"


def get_db_connection():
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        SECURITY_DB,
        timeout=10
    )

    connection.execute("PRAGMA busy_timeout = 10000")

    return connection


def initialize_security_db():
    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS pin_security (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until REAL NOT NULL DEFAULT 0
            )
        """)

        connection.execute("""
            INSERT OR IGNORE INTO pin_security (
                id,
                failed_attempts,
                locked_until
            )
            VALUES (1, 0, 0)
        """)


def get_lock_status():
    initialize_security_db()

    with get_db_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute("""
            SELECT failed_attempts, locked_until
            FROM pin_security
            WHERE id = 1
        """).fetchone()

        failed_attempts, locked_until = row
        now = time.time()

        if locked_until > 0 and now >= locked_until:
            connection.execute("""
                UPDATE pin_security
                SET failed_attempts = 0,
                    locked_until = 0
                WHERE id = 1
            """)

            failed_attempts = 0
            locked_until = 0

        connection.commit()

    return failed_attempts, locked_until


def register_failed_attempt():
    initialize_security_db()

    with get_db_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute("""
            SELECT failed_attempts, locked_until
            FROM pin_security
            WHERE id = 1
        """).fetchone()

        failed_attempts, locked_until = row
        now = time.time()

        if locked_until > now:
            connection.commit()
            return failed_attempts, locked_until

        if locked_until > 0 and now >= locked_until:
            failed_attempts = 0

        failed_attempts += 1

        if failed_attempts >= MAX_ATTEMPTS:
            locked_until = now + LOCKOUT_SECONDS
        else:
            locked_until = 0

        connection.execute("""
            UPDATE pin_security
            SET failed_attempts = ?,
                locked_until = ?
            WHERE id = 1
        """, (failed_attempts, locked_until))

        connection.commit()

    return failed_attempts, locked_until


def reset_failed_attempts():
    initialize_security_db()

    with get_db_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("""
            UPDATE pin_security
            SET failed_attempts = 0,
                locked_until = 0
            WHERE id = 1
        """)

        connection.commit()


def read_pin(prompt="Digite seu PIN: "):
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


def verify_pin(pin):
    if not isinstance(pin, str):
        return False

    if len(pin) != 8 or not pin.isdigit():
        return False

    stored_hash = get_required_env("ODIN_APPROVAL_PIN_HASH")

    try:
        algorithm, iterations_text, salt_hex, expected_hex = (
            stored_hash.split("$")
        )

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)

        if not 100_000 <= iterations <= 2_000_000:
            return False

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(expected_hex)

        if len(salt) != 16 or len(expected_hash) != 32:
            return False

        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            iterations
        )

        return hmac.compare_digest(
            calculated_hash,
            expected_hash
        )

    except (ValueError, TypeError):
        return False


def authenticate(max_attempts=MAX_ATTEMPTS, audit_manager=None):
    if max_attempts != MAX_ATTEMPTS:
        raise ValueError(
            "O limite de tentativas deve seguir a política de segurança."
        )

    try:
        failed_attempts, locked_until = get_lock_status()

    except sqlite3.Error:
        print("ODIN: Não foi possível verificar a segurança local.")
        print("Autenticação bloqueada por segurança.")
        return False

    # Inicializar o gerenciador de auditoria
    try:
        if audit_manager is None:
            audit_manager = AuditManager()

    except Exception:
        print("ODIN: Não foi possível inicializar a auditoria.")
        print("Autenticação bloqueada por segurança.")
        return False

    def log_auth_event(event_type, details=None):
        audit_manager.log_event(
            event_type=event_type,
            actor="ODIN",
            details=details or {}
        )

    # Verificar bloqueio ativo
    if locked_until > time.time():
        remaining = int(locked_until - time.time()) + 1

        try:
            log_auth_event(
                "pin_auth_locked",
                {
                    "reason": "active_lockout",
                    "remaining_seconds": remaining
                }
            )

        except Exception:
            print("ODIN: Falha no registro de auditoria.")
            print("Autenticação bloqueada por segurança.")
            return False

        print("\nODIN: AUTENTICAÇÃO BLOQUEADA.")
        print(f"Tente novamente em aproximadamente {remaining} segundos.")
        return False

    attempts_remaining = MAX_ATTEMPTS - failed_attempts

    while attempts_remaining > 0:

        try:
            pin = read_pin("ODIN - Digite seu PIN: ")

        except KeyboardInterrupt:
            print("\nODIN: Autenticação cancelada.")
            return False

        try:
            if verify_pin(pin):
                reset_failed_attempts()

                log_auth_event(
                    "pin_auth_success",
                    {
                        "result": "success"
                    }
                )

                print("ODIN: Identidade confirmada.")
                return True

            failed_attempts, locked_until = register_failed_attempt()

            log_auth_event(
                "pin_auth_failure",
                {
                    "failed_attempts": failed_attempts,
                    "attempts_remaining": max(
                        0,
                        MAX_ATTEMPTS - failed_attempts
                    )
                }
            )

            if locked_until > time.time():

                log_auth_event(
                    "pin_auth_locked",
                    {
                        "reason": "maximum_attempts_reached",
                        "failed_attempts": failed_attempts,
                        "lockout_seconds": LOCKOUT_SECONDS
                    }
                )

                print("\nODIN: LIMITE DE TENTATIVAS ATINGIDO.")
                print("Autenticação bloqueada por 15 minutos.")
                return False

            attempts_remaining = MAX_ATTEMPTS - failed_attempts

            print(
                f"PIN incorreto. Tentativas restantes: "
                f"{attempts_remaining}"
            )

        except Exception:
            print("\nODIN: Falha no sistema de autenticação.")
            print("Decisão bloqueada por segurança.")
            return False

    print("\nODIN: Acesso negado.")
    return False


initialize_security_db()
