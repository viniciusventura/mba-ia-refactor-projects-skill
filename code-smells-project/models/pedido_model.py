from models import produto_model
from utils.constants import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE


class PedidoInvalidoError(Exception):
    """Regra de domínio violada ao criar um pedido (produto inexistente, estoque insuficiente)."""


def criar(db, usuario_id, itens):
    """Cria pedido, itens e baixa de estoque numa transação única. Levanta PedidoInvalidoError."""
    produtos = produto_model.buscar_varios_para_pedido(db, {item["produto_id"] for item in itens})

    total = 0
    for item in itens:
        produto = produtos.get(item["produto_id"])
        if produto is None:
            raise PedidoInvalidoError("Produto " + str(item["produto_id"]) + " não encontrado")
        if produto["estoque"] < item["quantidade"]:
            raise PedidoInvalidoError("Estoque insuficiente para " + produto["nome"])
        total = total + (produto["preco"] * item["quantidade"])

    with db:  # commit no fim; rollback de tudo se qualquer passo falhar
        cur = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PENDENTE, total),
        )
        pedido_id = cur.lastrowid
        for item in itens:
            produto = produtos[item["produto_id"]]
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]),
            )
            # concorrência ou item repetido: a baixa condicional impede estoque negativo
            if not produto_model.baixar_estoque(db, item["produto_id"], item["quantidade"]):
                raise PedidoInvalidoError("Estoque insuficiente para " + produto["nome"])

    return {"pedido_id": pedido_id, "total": total}


def listar(db, usuario_id=None):
    """Pedidos com itens numa única query. Histórico: o nome do produto aparece mesmo se ele foi removido."""
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
    for r in db.execute(query, params).fetchall():
        pedido = pedidos.setdefault(r["id"], {
            "id": r["id"],
            "usuario_id": r["usuario_id"],
            "status": r["status"],
            "total": r["total"],
            "criado_em": r["criado_em"],
            "itens": [],
        })
        if r["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": r["produto_id"],
                "produto_nome": r["produto_nome"] if r["produto_nome"] is not None else "Desconhecido",
                "quantidade": r["quantidade"],
                "preco_unitario": r["preco_unitario"],
            })
    return list(pedidos.values())


def atualizar_status(db, pedido_id, novo_status):
    with db:
        cur = db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    return cur.rowcount > 0


def totais(db):
    row = db.execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COUNT(CASE WHEN status = ? THEN 1 END) AS pendentes,
               COUNT(CASE WHEN status = ? THEN 1 END) AS aprovados,
               COUNT(CASE WHEN status = ? THEN 1 END) AS cancelados
        FROM pedidos
        """,
        (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
    ).fetchone()
    return dict(row)


def contar(db):
    return db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
