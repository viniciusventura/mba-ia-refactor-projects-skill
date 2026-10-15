from models import pedido_model
from utils.constants import FAIXAS_DESCONTO


def calcular_desconto(faturamento):
    for limite, percentual in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * percentual
    return 0


def relatorio_vendas(db):
    # relatório é leitura histórica: inclui pedidos com produtos removidos
    t = pedido_model.totais(db)
    faturamento = t["faturamento"]
    desconto = calcular_desconto(faturamento)
    return {
        "total_pedidos": t["total_pedidos"],
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": t["pendentes"],
        "pedidos_aprovados": t["aprovados"],
        "pedidos_cancelados": t["cancelados"],
        "ticket_medio": round(faturamento / t["total_pedidos"], 2) if t["total_pedidos"] > 0 else 0,
    }
