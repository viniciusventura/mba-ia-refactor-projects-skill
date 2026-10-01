from flask import Blueprint

from controllers import sistema_controller
from middlewares.auth import require_admin_token

sistema_bp = Blueprint("sistema", __name__)

sistema_bp.add_url_rule("/", "index", sistema_controller.index, methods=["GET"])
sistema_bp.add_url_rule("/health", "health_check", sistema_controller.health_check, methods=["GET"])
sistema_bp.add_url_rule("/admin/reset-db", "reset_database", require_admin_token(sistema_controller.reset_database), methods=["POST"])
