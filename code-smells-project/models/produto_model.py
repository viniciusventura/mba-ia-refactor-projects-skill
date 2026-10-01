from database import transaction


def _to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def listar(db):
    rows = db.execute("SELECT * FROM produtos WHERE removido = 0 ORDER BY id").fetchall()
    return [_to_dict(row) for row in rows]


def buscar_por_id(db, id):
    row = db.execute("SELECT * FROM produtos WHERE id = ? AND removido = 0", (id,)).fetchone()
    return _to_dict(row) if row else None


def buscar(db, termo, categoria=None, preco_min=None, preco_max=None):
    query = "SELECT * FROM produtos WHERE removido = 0"
    params = []
    if termo:
        query += " AND (nome LIKE ? OR descricao LIKE ?)"
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if preco_min:
        query += " AND preco >= ?"
        params.append(preco_min)
    if preco_max:
        query += " AND preco <= ?"
        params.append(preco_max)
    rows = db.execute(query + " ORDER BY id", params).fetchall()
    return [_to_dict(row) for row in rows]


def criar(db, nome, descricao, preco, estoque, categoria):
    with transaction(db):
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(db, id, nome, descricao, preco, estoque, categoria):
    with transaction(db):
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? "
            "WHERE id = ? AND removido = 0",
            (nome, descricao, preco, estoque, categoria, id),
        )


def remover(db, id):
    """Soft delete: o produto sai das leituras de negócio, mas continua no histórico de pedidos."""
    with transaction(db):
        cursor = db.execute(
            "UPDATE produtos SET removido = 1, removido_em = CURRENT_TIMESTAMP WHERE id = ? AND removido = 0",
            (id,),
        )
    return cursor.rowcount > 0


def contar(db):
    return db.execute("SELECT COUNT(*) FROM produtos WHERE removido = 0").fetchone()[0]
