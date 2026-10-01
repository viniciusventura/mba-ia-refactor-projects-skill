from flask import Blueprint

from controllers import task_controller
from middlewares.auth import require_auth

task_bp = Blueprint('tasks', __name__)

task_bp.get('/tasks')(task_controller.get_tasks)
task_bp.get('/tasks/<int:task_id>')(task_controller.get_task)
task_bp.post('/tasks')(task_controller.create_task)
task_bp.put('/tasks/<int:task_id>')(task_controller.update_task)
task_bp.delete('/tasks/<int:task_id>')(require_auth()(task_controller.delete_task))
task_bp.get('/tasks/search')(task_controller.search_tasks)
task_bp.get('/tasks/stats')(task_controller.task_stats)
