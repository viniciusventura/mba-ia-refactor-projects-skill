from werkzeug.security import check_password_hash, generate_password_hash

from utils.constants import PAPEL_CLIENTE


def _to_dict(row):
    # serializador público: a senha (hash) nunca sai do model
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def listar(db):
    return [_to_dict(r) for r in db.execute("SELECT * FROM usuarios ORDER BY id").fetchall()]


def buscar_por_id(db, id):
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
    return _to_dict(row) if row else None


def criar(db, nome, email, senha, tipo=PAPEL_CLIENTE):
    with db:
        cur = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cur.lastrowid


def autenticar(db, email, senha):
    """Usuário (sem senha) se e-mail e senha conferem; senão None. A senha é verificada no código, não no SQL."""
    # a tabela não tem e-mail único: confere cada cadastro com o e-mail, como o SQL original fazia
    for row in db.execute("SELECT * FROM usuarios WHERE email = ? ORDER BY id", (email,)).fetchall():
        if row["senha"] and check_password_hash(row["senha"], senha):
            return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None


def contar(db):
    return db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
