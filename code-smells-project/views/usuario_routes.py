from flask import Blueprint

from controllers import usuario_controller
from middlewares.auth import require_auth
from utils.constants import PAPEL_ADMIN

usuario_bp = Blueprint("usuarios", __name__)

usuario_bp.add_url_rule("/usuarios", "listar_usuarios", require_auth(papel=PAPEL_ADMIN)(usuario_controller.listar_usuarios), methods=["GET"])
usuario_bp.add_url_rule("/usuarios/<int:id>", "buscar_usuario", require_auth()(usuario_controller.buscar_usuario), methods=["GET"])
usuario_bp.add_url_rule("/usuarios", "criar_usuario", usuario_controller.criar_usuario, methods=["POST"])
usuario_bp.add_url_rule("/login", "login", usuario_controller.login, methods=["POST"])
