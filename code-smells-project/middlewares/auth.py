from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from middlewares.error_handler import ForbiddenError, UnauthorizedError
from utils.constants import PAPEL_ADMIN


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def emitir_token(usuario):
    return _serializer().dumps({"id": usuario["id"], "tipo": usuario["tipo"]})


def require_auth(papel=None):
    """Exige 'Authorization: Bearer <token>' (401) e, se informado, o papel do usuário (403)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip()
            if not token:
                raise UnauthorizedError("Token ausente")
            try:
                g.usuario = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
            except (BadSignature, SignatureExpired):
                raise UnauthorizedError("Token inválido ou expirado")
            if papel and g.usuario.get("tipo") != papel:
                raise ForbiddenError("Acesso negado")
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def exigir_dono_ou_admin(usuario_id):
    """Para rotas com require_auth(): só o próprio usuário ou um admin."""
    if g.usuario["id"] != usuario_id and g.usuario.get("tipo") != PAPEL_ADMIN:
        raise ForbiddenError("Acesso negado")
