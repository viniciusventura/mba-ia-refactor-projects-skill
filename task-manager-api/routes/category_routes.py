from flask import Blueprint

from controllers import category_controller
from middlewares.auth import require_auth
from utils.constants import ADMIN_ROLE

category_bp = Blueprint('categories', __name__)

admin_only = require_auth(roles=(ADMIN_ROLE,))

category_bp.get('/categories')(category_controller.list_categories)
category_bp.post('/categories')(admin_only(category_controller.create_category))
category_bp.put('/categories/<int:category_id>')(admin_only(category_controller.update_category))
category_bp.delete('/categories/<int:category_id>')(admin_only(category_controller.delete_category))
