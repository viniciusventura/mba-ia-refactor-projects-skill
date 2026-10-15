from flask import Blueprint

from controllers import admin_controller
from middlewares.auth import require_auth
from utils.constants import PAPEL_ADMIN

admin_bp = Blueprint("admin", __name__)

# /admin/query (SQL arbitrário vindo do body) foi removida: F-05
admin_bp.add_url_rule("/admin/reset-db", "reset_database", require_auth(papel=PAPEL_ADMIN)(admin_controller.reset_database), methods=["POST"])
