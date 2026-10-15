from flask import Blueprint

from controllers import report_controller
from middlewares.auth import require_auth

report_bp = Blueprint('reports', __name__)

report_bp.get('/reports/summary')(require_auth()(report_controller.summary_report))
report_bp.get('/reports/user/<int:user_id>')(require_auth()(report_controller.user_report))
