import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, mensagem, **extra):
        """extra: chaves adicionais do contrato original (ex.: sucesso=False)."""
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.extra = extra


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.mensagem, **err.extra}), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # 404/405 do próprio Flask seguem com a resposta padrão do framework
        if isinstance(err, HTTPException):
            return err
        logger.exception("Erro inesperado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
