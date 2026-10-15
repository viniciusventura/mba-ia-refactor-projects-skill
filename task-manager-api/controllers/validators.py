import re
from datetime import datetime
from numbers import Number

from flask import request

from middlewares.error_handler import ValidationError
from utils.constants import (DUE_DATE_FORMAT, EMAIL_PATTERN, MAX_PRIORITY, MAX_TITLE_LENGTH, MIN_PRIORITY,
                             MIN_TITLE_LENGTH, TASK_STATUSES)

INVALID_DATA = 'Dados inválidos'


def json_body(allow_empty=False):
    """Body JSON como dict. allow_empty preserva endpoints que aceitavam {}."""
    data = request.get_json()
    if not isinstance(data, dict) or (not data and not allow_empty):
        raise ValidationError(INVALID_DATA)
    return data


def validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def validate_status(status):
    if status not in TASK_STATUSES:
        raise ValidationError('Status inválido')
    return status


def validate_priority(priority):
    is_number = isinstance(priority, Number) and not isinstance(priority, bool)
    if not is_number or priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
    return priority


def parse_due_date(value, error_message):
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(error_message)


def is_valid_email(email):
    return isinstance(email, str) and re.match(EMAIL_PATTERN, email) is not None


def optional_int_arg(name, error_message):
    raw = request.args.get(name, '')
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(error_message)
