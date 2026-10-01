from flask import Blueprint

from controllers import admin_controller
from middlewares.auth import require_auth
from utils.constants import TIPO_ADMIN

admin_bp = Blueprint("admin", __name__)
admin_bp.post("/admin/reset-db")(require_auth(tipo=TIPO_ADMIN)(admin_controller.reset_database))
