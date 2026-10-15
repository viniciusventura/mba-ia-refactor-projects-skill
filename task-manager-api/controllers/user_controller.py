import logging

from flask import g, jsonify

from controllers import validators
from database import db
from middlewares.auth import authenticate_optional, issue_token
from middlewares.error_handler import (ConflictError, ForbiddenError, NotFoundError, UnauthorizedError,
                                       ValidationError)
from models.task import Task
from models.user import User
from utils.constants import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, USER_ROLES

logger = logging.getLogger(__name__)

USER_NOT_FOUND = 'Usuário não encontrado'
INVALID_CREDENTIALS = 'Credenciais inválidas'


def _get_user_or_404(user_id):
    user = User.get_active(user_id)
    if user is None:
        raise NotFoundError(USER_NOT_FOUND)
    return user


def list_users():
    task_counts = Task.active_count_by_user()
    result = []
    for user in User.list_active():
        data = user.to_dict()
        data['task_count'] = task_counts.get(user.id, 0)
        result.append(data)
    return jsonify(result), 200


def get_user(user_id):
    user = _get_user_or_404(user_id)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in Task.list_by_user(user_id)]
    return jsonify(data), 200


def create_user():
    data = validators.json_body()
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
    if not validators.is_valid_email(email):
        raise ValidationError('Email inválido')
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    if User.find_by_email(email):
        raise ConflictError('Email já cadastrado')
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')
    if role != DEFAULT_ROLE:
        requester = authenticate_optional()
        if requester is None:
            raise UnauthorizedError('Token inválido ou ausente')
        if not requester.is_admin():
            raise ForbiddenError('Apenas admin pode criar usuários com este papel')

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado: %s - %s', user.id, user.name)
    return jsonify(user.to_dict()), 201


def update_user(user_id):
    user = _get_user_or_404(user_id)
    requester = g.current_user
    if requester.id != user.id and not requester.is_admin():
        raise ForbiddenError('Acesso negado')
    data = validators.json_body()
    if ('role' in data or 'active' in data) and not requester.is_admin():
        raise ForbiddenError('Apenas admin pode alterar role ou active')

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        if not validators.is_valid_email(data['email']):
            raise ValidationError('Email inválido')
        existing = User.find_by_email(data['email'])
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
        user.email = data['email']
    if 'password' in data:
        if not isinstance(data['password'], str) or len(data['password']) < MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha muito curta')
        user.set_password(data['password'])
    if 'role' in data:
        if data['role'] not in USER_ROLES:
            raise ValidationError('Role inválido')
        user.role = data['role']
    if 'active' in data:
        user.active = data['active']

    db.session.commit()
    return jsonify(user.to_dict()), 200


def delete_user(user_id):
    user = _get_user_or_404(user_id)
    deleted_by = g.current_user.id
    # cascata lógica: o original apagava as tasks do usuário; agora elas são marcadas na mesma transação
    for task in Task.list_by_user(user_id):
        task.mark_deleted(deleted_by)
    user.mark_deleted(deleted_by)
    db.session.commit()
    logger.info('Usuário %s removido (soft delete) por %s', user_id, deleted_by)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


def get_user_tasks(user_id):
    _get_user_or_404(user_id)
    return jsonify([task.to_summary_dict() for task in Task.list_by_user(user_id)]), 200


def login():
    data = validators.json_body()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_active_by_email(email)
    if user is None or not isinstance(password, str) or not user.check_password(password):
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    if user.has_legacy_password_hash():
        user.set_password(password)
        db.session.commit()

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user),
    }), 200
