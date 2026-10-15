from database import db
from utils.time import utc_now


class SoftDeleteMixin:
    """Exclusão lógica: o registro continua no banco com quando (deleted_at) e quem (deleted_by) removeu."""

    deleted = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)

    def mark_deleted(self, deleted_by):
        self.deleted = True
        self.deleted_at = utc_now()
        self.deleted_by = deleted_by

    @classmethod
    def not_deleted(cls):
        return cls.query.filter(cls.deleted.is_(False))

    @classmethod
    def find_by_id(cls, entity_id):
        """Inclui removidos (leituras históricas)."""
        return db.session.get(cls, entity_id)

    @classmethod
    def count(cls, include_deleted=False):
        return (cls.query if include_deleted else cls.not_deleted()).count()

    @classmethod
    def get_active(cls, entity_id):
        entity = db.session.get(cls, entity_id)
        if entity is None or entity.deleted:
            return None
        return entity
