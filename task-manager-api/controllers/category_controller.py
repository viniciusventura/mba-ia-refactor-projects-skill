import logging

from flask import g, jsonify

from controllers.validators import get_json_body
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from utils.constants import DEFAULT_COLOR

logger = logging.getLogger(__name__)


def _get_category_or_404(category_id):
    category = Category.get_not_deleted(category_id)
    if category is None:
        raise NotFoundError('Categoria não encontrada')
    return category


def get_categories():
    task_counts = Task.count_by_category()
    result = []
    for category in Category.not_deleted().all():
        category_data = category.to_dict()
        category_data['task_count'] = task_counts.get(category.id, 0)
        result.append(category_data)
    return jsonify(result), 200


def create_category():
    data = get_json_body()
    name = data.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')

    category = Category(
        name=name,
        description=data.get('description', ''),
        color=data.get('color', DEFAULT_COLOR),
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


def update_category(cat_id):
    category = _get_category_or_404(cat_id)
    data = get_json_body()
    for field in ('name', 'description', 'color'):
        if field in data:
            setattr(category, field, data[field])
    db.session.commit()
    return jsonify(category.to_dict()), 200


def delete_category(cat_id):
    category = _get_category_or_404(cat_id)
    # as tasks mantêm o category_id: a classificação histórica não é perdida
    category.mark_deleted(g.current_user.id)
    db.session.commit()
    logger.info('Categoria %s removida (soft delete) por usuário %s', cat_id, g.current_user.id)
    return jsonify({'message': 'Categoria deletada'}), 200
