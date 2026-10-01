CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def to_dict(row):
    return {campo: row[campo] for campo in CAMPOS}


def listar(db):
    rows = db.execute("SELECT * FROM produtos").fetchall()
    return [to_dict(row) for row in rows]


def buscar_por_id(db, id):
    row = db.execute("SELECT * FROM produtos WHERE id = ?", (id,)).fetchone()
    return to_dict(row) if row else None


def criar(db, nome, descricao, preco, estoque, categoria):
    with db:
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(db, id, nome, descricao, preco, estoque, categoria):
    with db:
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, id),
        )


def deletar(db, id):
    # Os itens de pedidos antigos são mantidos como histórico ("produto_nome": "Desconhecido").
    with db:
        db.execute("DELETE FROM produtos WHERE id = ?", (id,))


def buscar(db, termo, categoria=None, preco_min=None, preco_max=None):
    query = "SELECT * FROM produtos WHERE 1=1"
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
    rows = db.execute(query, params).fetchall()
    return [to_dict(row) for row in rows]
