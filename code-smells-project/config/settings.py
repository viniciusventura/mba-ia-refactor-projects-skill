import os
import secrets


class Settings:
    """Configuração única da aplicação, lida do ambiente (12-Factor)."""

    # Sem segredo fixo no código: sem SECRET_KEY no ambiente, uma chave aleatória é
    # gerada a cada boot (tokens emitidos antes de um restart deixam de valer).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    APP_ENV = os.environ.get("APP_ENV", "producao")
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "3600"))
