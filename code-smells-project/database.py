import logging
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        removido INTEGER NOT NULL DEFAULT 0,
        removido_em TIMESTAMP,
        removido_por INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
]

PRODUTOS_INICIAIS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

USUARIOS_INICIAIS = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]

# prefixos dos formatos gerados por werkzeug.security.generate_password_hash
_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Conexão da requisição atual (uma por contexto de app, fechada no teardown)."""
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())


def init_schema(db):
    with db:
        for ddl in SCHEMA:
            db.execute(ddl)
        # bancos criados antes do soft delete não têm estas colunas
        _garantir_coluna(db, "produtos", "removido", "removido INTEGER NOT NULL DEFAULT 0")
        _garantir_coluna(db, "produtos", "removido_em", "removido_em TIMESTAMP")
        _garantir_coluna(db, "produtos", "removido_por", "removido_por INTEGER")
        _migrar_senhas_em_texto(db)
        _seed(db)


def _garantir_coluna(db, tabela, coluna, ddl):
    # tabela/coluna/ddl são nomes internos fixos, nunca entrada do usuário
    colunas = {row["name"] for row in db.execute(f"PRAGMA table_info({tabela})")}
    if coluna not in colunas:
        db.execute(f"ALTER TABLE {tabela} ADD COLUMN {ddl}")
        logger.info("Migração: coluna %s.%s adicionada", tabela, coluna)


def _eh_hash(senha):
    return bool(senha) and senha.startswith(_PREFIXOS_HASH) and senha.count("$") == 2


def _migrar_senhas_em_texto(db):
    rows = db.execute("SELECT id, senha FROM usuarios").fetchall()
    pendentes = [(generate_password_hash(r["senha"]), r["id"]) for r in rows if r["senha"] and not _eh_hash(r["senha"])]
    if pendentes:
        db.executemany("UPDATE usuarios SET senha = ? WHERE id = ?", pendentes)
        logger.info("Migração: %d senha(s) em texto puro convertidas para hash", len(pendentes))


def _seed(db):
    if db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    db.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        PRODUTOS_INICIAIS,
    )
    db.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, generate_password_hash(senha), tipo) for nome, email, senha, tipo in USUARIOS_INICIAIS],
    )
