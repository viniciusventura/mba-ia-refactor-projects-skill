import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env_bool(name, default):
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def _secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    logger.warning('SECRET_KEY não definida: usando chave aleatória (tokens invalidam a cada restart)')
    return secrets.token_hex(32)


class Settings:
    SECRET_KEY = _secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '3600'))
    DEBUG = _env_bool('DEBUG', 'false')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', '5000'))
