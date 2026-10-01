import os
import secrets


def _bool(valor):
    return str(valor).lower() in ("1", "true", "yes", "sim")


class Settings:
    # Sem SECRET_KEY no ambiente, uma chave aleatória é gerada a cada boot.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _bool(os.environ.get("FLASK_DEBUG", "false"))
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    # Sem ADMIN_TOKEN, as rotas administrativas ficam sempre bloqueadas (401).
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or None
    AMBIENTE = os.environ.get("AMBIENTE", "producao")
