from werkzeug.security import check_password_hash, generate_password_hash

from utils.constants import TIPO_USUARIO_PADRAO

# Campos públicos: a senha (hash) nunca sai do model.
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_LOGIN = ("id", "nome", "email", "tipo")


def to_dict(row, campos=CAMPOS_PUBLICOS):
    return {campo: row[campo] for campo in campos}


def listar(db):
    rows = db.execute("SELECT * FROM usuarios").fetchall()
    return [to_dict(row) for row in rows]


def buscar_por_id(db, id):
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
    return to_dict(row) if row else None


def criar(db, nome, email, senha, tipo=TIPO_USUARIO_PADRAO):
    with db:
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid


def autenticar(db, email, senha):
    """Devolve os dados de login do usuário cujo e-mail e senha conferem, ou None."""
    rows = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchall()
    for row in rows:
        if row["senha"] and check_password_hash(row["senha"], senha):
            return to_dict(row, CAMPOS_LOGIN)
    return None
