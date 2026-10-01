from flask import Blueprint

from controllers import usuario_controller

usuario_bp = Blueprint("usuarios", __name__)
usuario_bp.get("/usuarios")(usuario_controller.listar_usuarios)
usuario_bp.get("/usuarios/<int:id>")(usuario_controller.buscar_usuario)
usuario_bp.post("/usuarios")(usuario_controller.criar_usuario)
usuario_bp.post("/login")(usuario_controller.login)
