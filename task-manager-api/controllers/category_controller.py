import logging

from flask import g, jsonify

from controllers import validators
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from utils.constants import DEFAULT_CATEGORY_COLOR

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND = 'Categoria não encontrada'


def _get_category_or_404(category_id):
    category = Category.get_active(category_id)
    if category is None:
        raise NotFoundError(CATEGORY_NOT_FOUND)
    return category


def list_categories():
    task_counts = Task.active_count_by_category()
    result = []
    for category in Category.list_active():
        data = category.to_dict()
        data['task_count'] = task_counts.get(category.id, 0)
        result.append(data)
    return jsonify(result), 200


def create_category():
    data = validators.json_body()
    name = data.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')

    category = Category(name=name, description=data.get('description', ''),
                        color=data.get('color', DEFAULT_CATEGORY_COLOR))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


def update_category(category_id):
    category = _get_category_or_404(category_id)
    data = validators.json_body(allow_empty=True)
    if 'name' in data:
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    if 'color' in data:
        category.color = data['color']
    db.session.commit()
    return jsonify(category.to_dict()), 200


def delete_category(category_id):
    category = _get_category_or_404(category_id)
    category.mark_deleted(g.current_user.id)
    db.session.commit()
    logger.info('Categoria %s removida (soft delete) por %s', category_id, g.current_user.id)
    return jsonify({'message': 'Categoria deletada'}), 200
