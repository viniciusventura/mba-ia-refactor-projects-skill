from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from middlewares.error_handler import ForbiddenError, UnauthorizedError


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def emitir_token(usuario):
    """Token assinado com o id e o tipo do usuário (expira em TOKEN_MAX_AGE segundos)."""
    return _serializer().dumps({"id": usuario["id"], "tipo": usuario["tipo"]})


def require_auth(tipo=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip()
            try:
                g.usuario = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
            except (BadSignature, SignatureExpired):
                raise UnauthorizedError("Token inválido ou ausente")
            if tipo and g.usuario.get("tipo") != tipo:
                raise ForbiddenError("Acesso negado")
            return fn(*args, **kwargs)
        return wrapper
    return decorator
