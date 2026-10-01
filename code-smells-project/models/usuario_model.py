from werkzeug.security import check_password_hash, generate_password_hash

from database import transaction
from utils.constants import TIPO_USUARIO_PADRAO


def _to_dict(row):
    """Representação pública do usuário: nunca inclui a senha."""
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def listar(db):
    rows = db.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
    return [_to_dict(row) for row in rows]


def buscar_por_id(db, id):
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
    return _to_dict(row) if row else None


def autenticar(db, email, senha):
    """Retorna o usuário cujo e-mail e senha conferem, ou None. A senha é verificada pelo hash."""
    rows = db.execute("SELECT * FROM usuarios WHERE email = ? ORDER BY id", (email,)).fetchall()
    for row in rows:
        if row["senha"] and check_password_hash(row["senha"], senha):
            return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None


def criar(db, nome, email, senha, tipo=TIPO_USUARIO_PADRAO):
    with transaction(db):
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid


def contar(db):
    return db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
