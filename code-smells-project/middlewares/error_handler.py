import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, message, extra=None):
        super().__init__(message)
        self.message = message
        # extra preserva o formato original de cada resposta (ex.: {"sucesso": False}).
        self.extra = extra or {}


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class NotFoundError(AppError):
    status_code = 404


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, **err.extra}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        # 404/405 do próprio Flask mantêm a resposta padrão (contrato original).
        return err

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro inesperado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
