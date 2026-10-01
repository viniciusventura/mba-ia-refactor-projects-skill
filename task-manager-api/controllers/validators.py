"""Validação de entrada compartilhada pelos controllers (borda HTTP → tipos do domínio)."""
from datetime import datetime

from flask import request

from middlewares.error_handler import ValidationError
from utils.constants import DUE_DATE_FORMAT


def get_json_body():
    data = request.get_json()          # sem silent: JSON malformado/content-type errado mantêm 400/415 do Flask
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def parse_due_date(value, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except ValueError:
        raise ValidationError(message)


def parse_int_arg(name, message):
    value = request.args.get(name, '')
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(message)
