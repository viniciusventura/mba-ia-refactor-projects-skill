from numbers import Number

from utils.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN

_COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


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


def _eh_numero(valor):
    return isinstance(valor, Number) and not isinstance(valor, bool)


def validar(dados):
    """Valida o payload de criação/edição. Devolve (mensagem_de_erro, None) ou (None, campos normalizados)."""
    if not dados or not isinstance(dados, dict):
        return "Dados inválidos", None
    if "nome" not in dados:
        return "Nome é obrigatório", None
    if "preco" not in dados:
        return "Preço é obrigatório", None
    if "estoque" not in dados:
        return "Estoque é obrigatório", None

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        return "Nome inválido", None
    if not isinstance(descricao, str):
        return "Descrição inválida", None
    if not _eh_numero(preco):
        return "Preço inválido", None
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        return "Estoque inválido", None
    if preco < 0:
        return "Preço não pode ser negativo", None
    if estoque < 0:
        return "Estoque não pode ser negativo", None
    if len(nome) < NOME_PRODUTO_MIN:
        return "Nome muito curto", None
    if len(nome) > NOME_PRODUTO_MAX:
        return "Nome muito longo", None
    if categoria not in CATEGORIAS_VALIDAS:
        return "Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS), None

    return None, {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def listar(db):
    rows = db.execute(f"SELECT {_COLUNAS} FROM produtos WHERE removido = 0 ORDER BY id").fetchall()
    return [_to_dict(r) for r in rows]


def buscar_por_id(db, id):
    row = db.execute(f"SELECT {_COLUNAS} FROM produtos WHERE id = ? AND removido = 0", (id,)).fetchone()
    return _to_dict(row) if row else None


def buscar(db, termo, categoria=None, preco_min=None, preco_max=None):
    query = f"SELECT {_COLUNAS} FROM produtos WHERE removido = 0"
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
    query += " ORDER BY id"
    return [_to_dict(r) for r in db.execute(query, params).fetchall()]


def buscar_varios_para_pedido(db, ids):
    """Produtos ativos por id, num único SELECT (id -> row)."""
    if not ids:
        return {}
    marcadores = ", ".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT id, nome, preco, estoque FROM produtos WHERE removido = 0 AND id IN ({marcadores})", list(ids)
    ).fetchall()
    return {r["id"]: r for r in rows}


def criar(db, nome, descricao, preco, estoque, categoria):
    with db:
        cur = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cur.lastrowid


def atualizar(db, id, nome, descricao, preco, estoque, categoria):
    with db:
        cur = db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? "
            "WHERE id = ? AND removido = 0",
            (nome, descricao, preco, estoque, categoria, id),
        )
    return cur.rowcount > 0


def remover(db, id, removido_por):
    """Soft delete: o produto some das leituras de negócio, mas continua no histórico de pedidos."""
    with db:
        cur = db.execute(
            "UPDATE produtos SET removido = 1, removido_em = CURRENT_TIMESTAMP, removido_por = ? "
            "WHERE id = ? AND removido = 0",
            (removido_por, id),
        )
    return cur.rowcount > 0


def baixar_estoque(db, produto_id, quantidade):
    """Baixa atômica: só baixa se houver estoque. Não faz commit (roda dentro da transação do pedido)."""
    cur = db.execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND removido = 0 AND estoque >= ?",
        (quantidade, produto_id, quantidade),
    )
    return cur.rowcount > 0


def contar(db):
    return db.execute("SELECT COUNT(*) FROM produtos WHERE removido = 0").fetchone()[0]
