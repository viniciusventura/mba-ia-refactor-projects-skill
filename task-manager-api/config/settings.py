import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default='false'):
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes')


class Settings:
    # Sem SECRET_KEY no ambiente, gera uma chave aleatória por boot (tokens emitidos expiram a cada restart)
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = _env_bool('FLASK_DEBUG')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', '5000'))
    TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '3600'))
