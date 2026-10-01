from views.pedido_routes import pedido_bp
from views.produto_routes import produto_bp
from views.relatorio_routes import relatorio_bp
from views.sistema_routes import sistema_bp
from views.usuario_routes import usuario_bp


def register_blueprints(app):
    for bp in (sistema_bp, produto_bp, usuario_bp, pedido_bp, relatorio_bp):
        app.register_blueprint(bp)
