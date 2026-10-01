from flask import Blueprint

from controllers import user_controller
from middlewares.auth import require_auth
from utils.constants import ADMIN_ROLE

user_bp = Blueprint('users', __name__)

user_bp.get('/users')(user_controller.get_users)
user_bp.get('/users/<int:user_id>')(user_controller.get_user)
user_bp.post('/users')(user_controller.create_user)
user_bp.put('/users/<int:user_id>')(user_controller.update_user)
user_bp.delete('/users/<int:user_id>')(require_auth(roles=(ADMIN_ROLE,))(user_controller.delete_user))
user_bp.get('/users/<int:user_id>/tasks')(user_controller.get_user_tasks)
user_bp.post('/login')(user_controller.login)
