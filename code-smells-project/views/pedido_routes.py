from flask import Blueprint

from controllers import pedido_controller
from middlewares.auth import require_auth
from utils.constants import PAPEL_ADMIN

pedido_bp = Blueprint("pedidos", __name__)
admin_only = require_auth(papel=PAPEL_ADMIN)
autenticado = require_auth()

pedido_bp.add_url_rule("/pedidos", "criar_pedido", autenticado(pedido_controller.criar_pedido), methods=["POST"])
pedido_bp.add_url_rule("/pedidos", "listar_todos_pedidos", admin_only(pedido_controller.listar_todos_pedidos), methods=["GET"])
pedido_bp.add_url_rule("/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario", autenticado(pedido_controller.listar_pedidos_usuario), methods=["GET"])
pedido_bp.add_url_rule("/pedidos/<int:pedido_id>/status", "atualizar_status_pedido", admin_only(pedido_controller.atualizar_status_pedido), methods=["PUT"])
