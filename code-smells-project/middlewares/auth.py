import hmac
from functools import wraps

from flask import current_app, request

from middlewares.error_handler import UnauthorizedError


def require_admin_token(fn):
    """Exige 'Authorization: Bearer <ADMIN_TOKEN>'. Sem ADMIN_TOKEN configurado, nega sempre."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        esperado = current_app.config.get("ADMIN_TOKEN")
        cabecalho = request.headers.get("Authorization", "")
        token = cabecalho.removeprefix("Bearer ").strip()
        if not esperado or not token or not hmac.compare_digest(token.encode(), esperado.encode()):
            raise UnauthorizedError("Não autorizado", {"sucesso": False})
        return fn(*args, **kwargs)
    return wrapper
