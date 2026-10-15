from flask import request


def ler_json():
    """Body JSON da requisição, ou None se ausente/malformado (vira 400 no controller, não 500)."""
    return request.get_json(silent=True)


def eh_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)
