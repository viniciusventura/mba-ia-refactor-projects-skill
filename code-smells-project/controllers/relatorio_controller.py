from flask import jsonify

from database import get_db
from models import relatorio_model


def relatorio_vendas():
    totais = relatorio_model.totais_vendas(get_db())
    faturamento = totais["faturamento"]
    total_pedidos = totais["total_pedidos"]
    desconto = relatorio_model.calcular_desconto(faturamento)

    relatorio = {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": totais["pendentes"],
        "pedidos_aprovados": totais["aprovados"],
        "pedidos_cancelados": totais["cancelados"],
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
    return jsonify({"dados": relatorio, "sucesso": True}), 200
