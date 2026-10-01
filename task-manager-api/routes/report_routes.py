from flask import Blueprint

from controllers import report_controller

report_bp = Blueprint('reports', __name__)

report_bp.get('/reports/summary')(report_controller.summary_report)
report_bp.get('/reports/user/<int:user_id>')(report_controller.user_report)
