from flask import Blueprint

from controllers import category_controller
from middlewares.auth import require_auth
from utils.constants import ADMIN_ROLE

category_bp = Blueprint('categories', __name__)

category_bp.get('/categories')(category_controller.get_categories)
category_bp.post('/categories')(category_controller.create_category)
category_bp.put('/categories/<int:cat_id>')(category_controller.update_category)
category_bp.delete('/categories/<int:cat_id>')(require_auth(roles=(ADMIN_ROLE,))(category_controller.delete_category))
