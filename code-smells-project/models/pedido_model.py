from utils.constants import FAIXAS_DESCONTO, STATUS_INICIAL_PEDIDO


class RegraPedidoError(Exception):
    """Violação de regra de negócio do pedido (produto inexistente, estoque insuficiente)."""


def criar(db, usuario_id, itens):
    """Cria o pedido, seus itens e a baixa de estoque numa única transação."""
    with db:
        ids = sorted({item["produto_id"] for item in itens})
        marcadores = ", ".join("?" for _ in ids)
        produtos = {
            row["id"]: row
            for row in db.execute(
                "SELECT id, nome, preco, estoque FROM produtos WHERE id IN (" + marcadores + ")", ids
            ).fetchall()
        }

        total = 0
        precos = {}
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise RegraPedidoError("Produto " + str(item["produto_id"]) + " não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise RegraPedidoError("Estoque insuficiente para " + produto["nome"])
            total = total + (produto["preco"] * item["quantidade"])
            precos[item["produto_id"]] = (produto["nome"], produto["preco"])

        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_INICIAL_PEDIDO, total),
        )
        pedido_id = cursor.lastrowid

        for item in itens:
            nome, preco = precos[item["produto_id"]]
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, item["produto_id"], item["quantidade"], preco),
            )
            # Baixa condicional: evita estoque negativo com pedidos concorrentes ou itens repetidos.
            baixa = db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (item["quantidade"], item["produto_id"], item["quantidade"]),
            )
            if baixa.rowcount == 0:
                raise RegraPedidoError("Estoque insuficiente para " + nome)

    return {"pedido_id": pedido_id, "total": total}


def listar(db, usuario_id=None):
    """Pedidos com itens numa única query (JOIN), na ordem de criação."""
    query = """
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
    """
    params = []
    if usuario_id is not None:
        query += " WHERE p.usuario_id = ?"
        params.append(usuario_id)
    query += " ORDER BY p.id, i.id"

    pedidos = {}
    for row in db.execute(query, params).fetchall():
        pedido = pedidos.setdefault(row["id"], {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] if row["produto_nome"] is not None else "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def atualizar_status(db, pedido_id, novo_status):
    """Devolve False se o pedido não existe."""
    with db:
        cursor = db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    return cursor.rowcount > 0


def totais_vendas(db):
    row = db.execute("""
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
    """).fetchone()
    return dict(row)


def calcular_desconto(faturamento):
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0
