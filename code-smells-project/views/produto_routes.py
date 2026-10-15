from flask import Blueprint

from controllers import produto_controller
from middlewares.auth import require_auth
from utils.constants import PAPEL_ADMIN

produto_bp = Blueprint("produtos", __name__)
admin_only = require_auth(papel=PAPEL_ADMIN)

produto_bp.add_url_rule("/produtos", "listar_produtos", produto_controller.listar_produtos, methods=["GET"])
produto_bp.add_url_rule("/produtos/busca", "buscar_produtos", produto_controller.buscar_produtos, methods=["GET"])
produto_bp.add_url_rule("/produtos/<int:id>", "buscar_produto", produto_controller.buscar_produto, methods=["GET"])
produto_bp.add_url_rule("/produtos", "criar_produto", admin_only(produto_controller.criar_produto), methods=["POST"])
produto_bp.add_url_rule("/produtos/<int:id>", "atualizar_produto", admin_only(produto_controller.atualizar_produto), methods=["PUT"])
produto_bp.add_url_rule("/produtos/<int:id>", "deletar_produto", admin_only(produto_controller.deletar_produto), methods=["DELETE"])
