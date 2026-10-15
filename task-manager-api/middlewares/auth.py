from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from middlewares.error_handler import ForbiddenError, UnauthorizedError
from models.user import User

_SALT = 'auth-token'


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SALT)


def issue_token(user):
    return _serializer().dumps({'id': user.id})


def _bearer_token():
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    return header.removeprefix('Bearer ').strip() or None


def authenticate_optional():
    """Usuário do token, ou None sem header. Token presente e inválido → 401."""
    token = _bearer_token()
    if token is None:
        return None
    try:
        payload = _serializer().loads(token, max_age=current_app.config['TOKEN_MAX_AGE'])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError('Token inválido ou ausente')
    user = User.get_active(payload.get('id'))
    if user is None:
        raise UnauthorizedError('Token inválido ou ausente')
    if not user.active:
        raise ForbiddenError('Usuário inativo')
    return user


def authenticate():
    user = authenticate_optional()
    if user is None:
        raise UnauthorizedError('Token inválido ou ausente')
    return user


def require_auth(roles=None):
    def decorator(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            g.current_user = authenticate()
            if roles and g.current_user.role not in roles:
                raise ForbiddenError('Acesso negado')
            return handler(*args, **kwargs)
        return wrapper
    return decorator
