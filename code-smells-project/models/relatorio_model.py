from utils.constants import FAIXAS_DESCONTO


def totais_vendas(db):
    """Totais de pedidos e faturamento em uma única agregação."""
    row = db.execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
        """
    ).fetchone()
    return dict(row)


def calcular_desconto(faturamento):
    """Regra de negócio: desconto aplicável conforme a faixa de faturamento."""
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0
