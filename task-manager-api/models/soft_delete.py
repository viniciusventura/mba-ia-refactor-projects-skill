from sqlalchemy.orm import declared_attr

from database import db
from utils.time import utc_now


class SoftDeleteMixin:
    """Exclusão lógica: o registro continua no banco com quando (deleted_at) e quem (deleted_by) removeu."""

    deleted = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    deleted_at = db.Column(db.DateTime, nullable=True)

    @declared_attr
    def deleted_by(cls):
        return db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    @classmethod
    def not_deleted(cls):
        return cls.query.filter_by(deleted=False)

    @classmethod
    def get_not_deleted(cls, record_id):
        return cls.not_deleted().filter_by(id=record_id).first()

    @classmethod
    def get_including_deleted(cls, record_id):
        """Leitura histórica (relatórios): também devolve registros removidos."""
        return cls.query.filter_by(id=record_id).first()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    def mark_deleted(self, deleted_by, when=None):
        self.deleted = True
        self.deleted_at = when or utc_now()
        self.deleted_by = deleted_by
