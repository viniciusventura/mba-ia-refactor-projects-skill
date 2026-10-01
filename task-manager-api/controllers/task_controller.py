import logging

from flask import g, jsonify, request

from controllers.validators import get_json_body, parse_due_date, parse_int_arg
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User
from utils.constants import (DEFAULT_PRIORITY, DEFAULT_TASK_STATUS, MAX_PRIORITY, MAX_TITLE_LENGTH,
                             MIN_PRIORITY, MIN_TITLE_LENGTH, TASK_STATUSES)
from utils.helpers import calculate_percentage
from utils.time import utc_now

logger = logging.getLogger(__name__)


# --- validação de entrada (compartilhada por create e update) ----------------

def _validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def _validate_status(status):
    if status not in TASK_STATUSES:
        raise ValidationError('Status inválido')
    return status


def _validate_priority(priority):
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValidationError('Prioridade inválida')
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
    return priority


def _ensure_user_exists(user_id):
    if user_id and User.get_not_deleted(user_id) is None:
        raise NotFoundError('Usuário não encontrado')


def _ensure_category_exists(category_id):
    if category_id and Category.get_not_deleted(category_id) is None:
        raise NotFoundError('Categoria não encontrada')


def _get_task_or_404(task_id):
    task = Task.get_not_deleted(task_id)
    if task is None:
        raise NotFoundError('Task não encontrada')
    return task


# --- handlers ------------------------------------------------------------------

def get_tasks():
    tasks = Task.list_active_with_relations()
    return jsonify([task.to_list_dict() for task in tasks]), 200


def get_task(task_id):
    return jsonify(_get_task_or_404(task_id).to_detail_dict()), 200


def create_task():
    data = get_json_body()

    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    _validate_title(title)

    status = _validate_status(data.get('status', DEFAULT_TASK_STATUS))
    priority = _validate_priority(data.get('priority', DEFAULT_PRIORITY))
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    _ensure_user_exists(user_id)
    _ensure_category_exists(category_id)

    task = Task(
        title=title,
        description=data.get('description', ''),
        status=status,
        priority=priority,
        user_id=user_id,
        category_id=category_id,
    )
    if data.get('due_date'):
        task.due_date = parse_due_date(data['due_date'], 'Formato de data inválido. Use YYYY-MM-DD')
    if data.get('tags'):
        task.set_tags(data['tags'])

    db.session.add(task)
    db.session.commit()
    logger.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = _get_task_or_404(task_id)
    data = get_json_body()

    changes = {}
    if 'title' in data:
        changes['title'] = _validate_title(data['title'])
    if 'description' in data:
        changes['description'] = data['description']
    if 'status' in data:
        changes['status'] = _validate_status(data['status'])
    if 'priority' in data:
        changes['priority'] = _validate_priority(data['priority'])
    if 'user_id' in data:
        _ensure_user_exists(data['user_id'])
        changes['user_id'] = data['user_id']
    if 'category_id' in data:
        _ensure_category_exists(data['category_id'])
        changes['category_id'] = data['category_id']
    if 'due_date' in data:
        changes['due_date'] = parse_due_date(data['due_date'], 'Formato de data inválido') if data['due_date'] else None

    for field, value in changes.items():
        setattr(task, field, value)
    if 'tags' in data:
        task.set_tags(data['tags'])
    task.updated_at = utc_now()

    db.session.commit()
    logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = _get_task_or_404(task_id)
    task.mark_deleted(g.current_user.id)
    db.session.commit()
    logger.info('Task %s removida (soft delete) por usuário %s', task_id, g.current_user.id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    tasks = Task.search(
        query=request.args.get('q', ''),
        status=request.args.get('status', ''),
        priority=parse_int_arg('priority', 'Prioridade inválida'),
        user_id=parse_int_arg('user_id', 'user_id inválido'),
    )
    return jsonify([task.to_dict() for task in tasks]), 200


def task_stats():
    by_status = Task.count_by_status()
    total = sum(by_status.values())
    done = by_status.get('done', 0)
    now = utc_now()
    overdue = sum(1 for task in Task.all_tasks() if task.is_overdue(now))

    return jsonify({
        'total': total,
        'pending': by_status.get('pending', 0),
        'in_progress': by_status.get('in_progress', 0),
        'done': done,
        'cancelled': by_status.get('cancelled', 0),
        'overdue': overdue,
        'completion_rate': calculate_percentage(done, total),
    }), 200
