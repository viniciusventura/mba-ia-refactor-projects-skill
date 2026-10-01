from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from middlewares.error_handler import ForbiddenError, UnauthorizedError
from models.user import User


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='auth')


def issue_token(user):
    return _serializer().dumps({'id': user.id})


def authenticate(roles=None):
    """Valida o Bearer token e devolve o usuário ativo; 401 sem token válido, 403 sem o papel exigido."""
    header = request.headers.get('Authorization', '')
    token = header.removeprefix('Bearer ').strip()
    if not token:
        raise UnauthorizedError('Token ausente')
    try:
        payload = _serializer().loads(token, max_age=current_app.config['TOKEN_MAX_AGE'])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError('Token inválido ou expirado')

    # o papel vem do banco, não do token: rebaixamento/remoção vale na hora
    user = User.get_not_deleted(payload.get('id'))
    if user is None or not user.active:
        raise UnauthorizedError('Token inválido ou expirado')
    if roles and user.role not in roles:
        raise ForbiddenError('Acesso negado')
    g.current_user = user
    return user


def require_auth(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            authenticate(roles)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
