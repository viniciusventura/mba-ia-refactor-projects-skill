import os
import secrets


def _bool(nome, padrao="false"):
    return os.environ.get(nome, padrao).strip().lower() in ("1", "true", "yes", "sim")


class Settings:
    # Sem SECRET_KEY no ambiente, uma chave aleatória é gerada por processo:
    # o app funciona, mas os tokens emitidos deixam de valer a cada restart.
    SECRET_KEY_DO_AMBIENTE = bool(os.environ.get("SECRET_KEY"))
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "3600"))
    APP_ENV = os.environ.get("APP_ENV", "producao")
