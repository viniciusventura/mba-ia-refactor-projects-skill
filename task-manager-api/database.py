from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()

SOFT_DELETE_TABLES = ('users', 'categories', 'tasks')
SOFT_DELETE_COLUMNS = {
    'deleted': 'deleted BOOLEAN NOT NULL DEFAULT 0',
    'deleted_at': 'deleted_at DATETIME',
    'deleted_by': 'deleted_by INTEGER',
}


def init_app(app):
    db.init_app(app)
    with app.app_context():
        import models  # noqa: F401  (registra as tabelas no metadata)
        db.create_all()
        _migrate_soft_delete_columns()


def _migrate_soft_delete_columns():
    """create_all() não altera tabelas existentes: adiciona as colunas de soft delete só se faltarem."""
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        for table in SOFT_DELETE_TABLES:
            existing = {column['name'] for column in inspector.get_columns(table)}
            for column, ddl in SOFT_DELETE_COLUMNS.items():
                if column not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {ddl}'))  # nomes internos fixos
