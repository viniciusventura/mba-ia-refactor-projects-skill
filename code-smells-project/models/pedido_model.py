from database import transaction
from utils.constants import STATUS_PEDIDO_INICIAL


class PedidoInvalidoError(Exception):
    """Regra de domínio violada ao criar um pedido (produto inexistente, estoque insuficiente)."""


def criar(db, usuario_id, itens):
    """Valida estoque, calcula o total e grava pedido, itens e baixa de estoque numa única transação."""
    with transaction(db):
        ids = [item["produto_id"] for item in itens]
        marcadores = ", ".join("?" for _ in ids)
        produtos = {
            row["id"]: row
            for row in db.execute(
                f"SELECT id, nome, preco, estoque FROM produtos WHERE removido = 0 AND id IN ({marcadores})", ids
            )
        }

        total = 0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise PedidoInvalidoError("Produto " + str(item["produto_id"]) + " não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise PedidoInvalidoError("Estoque insuficiente para " + produto["nome"])
            total = total + (produto["preco"] * item["quantidade"])

        pedido_id = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PEDIDO_INICIAL, total),
        ).lastrowid
        db.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            [(pedido_id, item["produto_id"], item["quantidade"], produtos[item["produto_id"]]["preco"]) for item in itens],
        )
        db.executemany(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
            [(item["quantidade"], item["produto_id"]) for item in itens],
        )
    return {"pedido_id": pedido_id, "total": total}


def _listar(db, where="", params=()):
    # Leitura histórica: o JOIN com produtos não filtra removidos, para manter o nome do produto.
    rows = db.execute(
        f"""
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
        {where}
        ORDER BY p.id, i.id
        """,
        params,
    ).fetchall()

    pedidos = {}
    for row in rows:
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
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def listar_todos(db):
    return _listar(db)


def listar_por_usuario(db, usuario_id):
    return _listar(db, "WHERE p.usuario_id = ?", (usuario_id,))


def atualizar_status(db, pedido_id, novo_status):
    with transaction(db):
        cursor = db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    return cursor.rowcount > 0


def contar(db):
    return db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
