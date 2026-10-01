import logging
import re

from flask import g, jsonify

from controllers.validators import get_json_body
from database import db
from middlewares.auth import authenticate, issue_token
from middlewares.error_handler import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from models.task import Task
from models.user import User
from utils.constants import ADMIN_ROLE, DEFAULT_ROLE, EMAIL_PATTERN, MIN_PASSWORD_LENGTH, USER_ROLES
from utils.time import utc_now

logger = logging.getLogger(__name__)


def _is_valid_email(email):
    return isinstance(email, str) and re.match(EMAIL_PATTERN, email) is not None


def _ensure_email_available(email, current_user_id=None):
    existing = User.find_by_email(email)
    if existing and existing.id != current_user_id:
        raise ConflictError('Email já cadastrado')


def _validate_role(role):
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')
    return role


def _get_user_or_404(user_id):
    user = User.get_not_deleted(user_id)
    if user is None:
        raise NotFoundError('Usuário não encontrado')
    return user


def get_users():
    task_counts = Task.count_by_user()
    result = []
    for user in User.not_deleted().all():
        user_data = user.to_dict()
        user_data['task_count'] = task_counts.get(user.id, 0)
        result.append(user_data)
    return jsonify(result), 200


def get_user(user_id):
    user = _get_user_or_404(user_id)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in Task.all_tasks(user_id=user_id)]
    return jsonify(data), 200


def create_user():
    data = get_json_body()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', DEFAULT_ROLE)

    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    if not _is_valid_email(email):
        raise ValidationError('Email inválido')
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    _ensure_email_available(email)
    _validate_role(role)
    if role != DEFAULT_ROLE:
        authenticate(roles=(ADMIN_ROLE,))      # só admin cria usuário com privilégio

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado: %s - %s', user.id, user.name)
    return jsonify(user.to_dict()), 201


def update_user(user_id):
    user = _get_user_or_404(user_id)
    data = get_json_body()

    if 'role' in data or 'active' in data:
        authenticate(roles=(ADMIN_ROLE,))      # privilégio e ativação só por admin

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        if not _is_valid_email(data['email']):
            raise ValidationError('Email inválido')
        _ensure_email_available(data['email'], current_user_id=user_id)
        user.email = data['email']
    if 'password' in data:
        if not isinstance(data['password'], str) or len(data['password']) < MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha muito curta')
        user.set_password(data['password'])
    if 'role' in data:
        user.role = _validate_role(data['role'])
    if 'active' in data:
        user.active = data['active']

    db.session.commit()
    return jsonify(user.to_dict()), 200


def delete_user(user_id):
    user = _get_user_or_404(user_id)
    now = utc_now()
    removed_by = g.current_user.id
    # cascata lógica: o original apagava as tasks do usuário; agora elas são marcadas, na mesma transação
    Task.soft_delete_by_user(user.id, removed_by, now)
    user.mark_deleted(removed_by, now)
    db.session.commit()
    logger.info('Usuário %s removido (soft delete) por usuário %s', user_id, removed_by)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


def get_user_tasks(user_id):
    _get_user_or_404(user_id)
    return jsonify([task.to_summary_dict() for task in Task.all_tasks(user_id=user_id)]), 200


def login():
    data = get_json_body()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_active_by_email(email)
    if user is None or not isinstance(password, str) or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user),
    }), 200
