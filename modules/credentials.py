"""
Gestión segura de credenciales usando Windows Credential Manager (keyring).
Las contraseñas se almacenan cifradas en el sistema operativo,
nunca en texto plano en el disco.

Uso inicial (una sola vez):
    python -m modules.credentials --setup
"""
import sys
import argparse
from modules.logger import get_logger

log = get_logger(__name__)

APP_NAME = "inna_asistente_virtual"

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


def save_credential(service: str, username: str, password: str):
    """
    Guarda una credencial de forma segura en Windows Credential Manager.

    Args:
        service: Nombre del servicio (ej: 'email', 'smtp').
        username: Usuario o clave identificadora.
        password: Valor secreto a cifrar.
    """
    if not KEYRING_AVAILABLE:
        raise ImportError("Instala keyring: pip install keyring")
    keyring.set_password(f"{APP_NAME}_{service}", username, password)
    log.info("Credencial guardada: %s/%s", service, username)


def get_credential(service: str, username: str) -> str | None:
    """
    Recupera una credencial almacenada.

    Returns:
        El valor secreto, o None si no existe.
    """
    if not KEYRING_AVAILABLE:
        return None
    return keyring.get_password(f"{APP_NAME}_{service}", username)


def delete_credential(service: str, username: str):
    """Elimina una credencial almacenada."""
    if not KEYRING_AVAILABLE:
        return
    try:
        keyring.delete_password(f"{APP_NAME}_{service}", username)
        log.info("Credencial eliminada: %s/%s", service, username)
    except keyring.errors.PasswordDeleteError:
        log.warning("No se encontro credencial para eliminar: %s/%s", service, username)


def get_email_password(email_user: str) -> str:
    """
    Obtiene la contraseña del correo. Busca primero en keyring,
    luego en variables de entorno como fallback.
    """
    # 1. Intentar desde keyring
    if KEYRING_AVAILABLE:
        pwd = get_credential("email", email_user)
        if pwd:
            log.debug("Contrasena de correo obtenida desde keyring.")
            return pwd

    # 2. Fallback a variable de entorno
    import os
    pwd = os.getenv("EMAIL_PASS", "")
    if pwd:
        log.debug("Contrasena de correo obtenida desde variable de entorno.")
        return pwd

    raise RuntimeError(
        "No se encontro contrasena para el correo.\n"
        "Ejecuta: python -m modules.credentials --setup"
    )


def setup_interactive():
    """Asistente interactivo para guardar credenciales de forma segura."""
    if not KEYRING_AVAILABLE:
        print("ERROR: keyring no instalado. Ejecuta: pip install keyring")
        sys.exit(1)

    print("\n=== Configuracion de credenciales seguras — Inna ===\n")
    print("Las contrasenas se guardaran en Windows Credential Manager.")
    print("No se almacenan en disco ni en archivos de texto.\n")

    email = input("Correo electronico: ").strip()
    password = input("App Password de Gmail (no tu contrasena normal): ").strip()

    if email and password:
        save_credential("email", email, password)
        print(f"\nCredencial guardada para: {email}")
        print("Ya puedes eliminar EMAIL_PASS de tu archivo .env\n")
    else:
        print("Datos incompletos. Operacion cancelada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestion de credenciales de Inna")
    parser.add_argument("--setup",  action="store_true", help="Configurar credenciales")
    parser.add_argument("--delete", metavar="EMAIL",     help="Eliminar credencial de un correo")
    args = parser.parse_args()

    if args.setup:
        setup_interactive()
    elif args.delete:
        delete_credential("email", args.delete)
        print(f"Credencial eliminada para: {args.delete}")
    else:
        parser.print_help()
