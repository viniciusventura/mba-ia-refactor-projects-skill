import logging

from flask import g, jsonify, request

from controllers import validators
from database import db
from middlewares.error_handler import ForbiddenError, NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User
from utils.constants import DEFAULT_PRIORITY, DEFAULT_TASK_STATUS, TASK_MANAGER_ROLES
from utils.time import utc_now

logger = logging.getLogger(__name__)

TASK_NOT_FOUND = 'Task não encontrada'


def _get_task_or_404(task_id):
    task = Task.get_active(task_id)
    if task is None:
        raise NotFoundError(TASK_NOT_FOUND)
    return task


def _ensure_can_modify(task):
    user = g.current_user
    if user.role not in TASK_MANAGER_ROLES and task.user_id != user.id:
        raise ForbiddenError('Acesso negado')


def _ensure_user_exists(user_id):
    if user_id and User.get_active(user_id) is None:
        raise NotFoundError('Usuário não encontrado')


def _ensure_category_exists(category_id):
    if category_id and Category.get_active(category_id) is None:
        raise NotFoundError('Categoria não encontrada')


def list_tasks():
    result = []
    for task in Task.list_active_with_relations():
        data = task.to_dict()
        data['overdue'] = task.is_overdue()
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return jsonify(result), 200


def get_task(task_id):
    task = _get_task_or_404(task_id)
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return jsonify(data), 200


def create_task():
    data = validators.json_body()
    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    validators.validate_title(title)
    status = validators.validate_status(data.get('status', DEFAULT_TASK_STATUS))
    priority = validators.validate_priority(data.get('priority', DEFAULT_PRIORITY))
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    _ensure_user_exists(user_id)
    _ensure_category_exists(category_id)

    task = Task(title=title, description=data.get('description', ''), status=status, priority=priority,
                user_id=user_id, category_id=category_id)
    if data.get('due_date'):
        task.due_date = validators.parse_due_date(data['due_date'], 'Formato de data inválido. Use YYYY-MM-DD')
    if data.get('tags'):
        task.set_tags(data['tags'])

    db.session.add(task)
    db.session.commit()
    logger.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = _get_task_or_404(task_id)
    _ensure_can_modify(task)
    data = validators.json_body()

    if 'title' in data:
        task.title = validators.validate_title(data['title'])
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = validators.validate_status(data['status'])
    if 'priority' in data:
        task.priority = validators.validate_priority(data['priority'])
    if 'user_id' in data:
        _ensure_user_exists(data['user_id'])
        task.user_id = data['user_id']
    if 'category_id' in data:
        _ensure_category_exists(data['category_id'])
        task.category_id = data['category_id']
    if 'due_date' in data:
        task.due_date = (validators.parse_due_date(data['due_date'], 'Formato de data inválido')
                         if data['due_date'] else None)
    if 'tags' in data:
        task.set_tags(data['tags'])

    task.updated_at = utc_now()
    db.session.commit()
    logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = _get_task_or_404(task_id)
    _ensure_can_modify(task)
    task.mark_deleted(g.current_user.id)
    db.session.commit()
    logger.info('Task %s removida (soft delete) por %s', task_id, g.current_user.id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    tasks = Task.search(
        text=request.args.get('q', ''),
        status=request.args.get('status', ''),
        priority=validators.optional_int_arg('priority', 'Prioridade inválida'),
        user_id=validators.optional_int_arg('user_id', 'user_id inválido'),
    )
    return jsonify([task.to_dict() for task in tasks]), 200


def task_stats():
    by_status = Task.count_by(Task.status)
    total = Task.count()
    done = by_status.get('done', 0)
    stats = {
        'total': total,
        'pending': by_status.get('pending', 0),
        'in_progress': by_status.get('in_progress', 0),
        'done': done,
        'cancelled': by_status.get('cancelled', 0),
        'overdue': sum(1 for task in Task.list_all() if task.is_overdue()),
        'completion_rate': Task.completion_rate(done, total),
    }
    return jsonify(stats), 200
