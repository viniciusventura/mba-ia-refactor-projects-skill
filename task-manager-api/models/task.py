from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from database import db
from models.soft_delete import SoftDeleteMixin
from utils.constants import CLOSED_TASK_STATUSES, DEFAULT_PRIORITY, DEFAULT_TASK_STATUS, DONE_STATUS
from utils.time import utc_now


class Task(SoftDeleteMixin, db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_TASK_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_summary_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    def is_overdue(self, now=None):
        now = now or utc_now()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_TASK_STATUSES)

    def set_tags(self, tags):
        self.tags = ','.join(tags) if isinstance(tags, list) else tags

    # --- leituras de negócio (ignoram tasks removidas) ---

    @classmethod
    def list_active_with_relations(cls):
        return (cls.not_deleted()
                .options(joinedload(cls.user), joinedload(cls.category))
                .order_by(cls.id)
                .all())

    @classmethod
    def list_by_user(cls, user_id, include_deleted=False):
        return cls._scope(include_deleted).filter_by(user_id=user_id).order_by(cls.id).all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = cls.not_deleted()
        if text:
            query = query.filter(db.or_(cls.title.like(f'%{text}%'), cls.description.like(f'%{text}%')))
        if status:
            query = query.filter(cls.status == status)
        if priority is not None:
            query = query.filter(cls.priority == priority)
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        return query.order_by(cls.id).all()

    @classmethod
    def active_count_by_user(cls):
        rows = db.session.query(cls.user_id, func.count(cls.id)).filter(cls.deleted.is_(False)).group_by(cls.user_id)
        return dict(rows.all())

    @classmethod
    def active_count_by_category(cls):
        rows = (db.session.query(cls.category_id, func.count(cls.id))
                .filter(cls.deleted.is_(False))
                .group_by(cls.category_id))
        return dict(rows.all())

    # --- agregações (include_deleted=True nas leituras históricas dos relatórios) ---

    @classmethod
    def _scope(cls, include_deleted):
        return cls.query if include_deleted else cls.not_deleted()

    @classmethod
    def count_by(cls, column, include_deleted=False):
        query = db.session.query(column, func.count(cls.id))
        if not include_deleted:
            query = query.filter(cls.deleted.is_(False))
        return dict(query.group_by(column).all())

    @classmethod
    def list_all(cls, include_deleted=False):
        return cls._scope(include_deleted).order_by(cls.id).all()

    @classmethod
    def count_created_since(cls, since, include_deleted=False):
        return cls._scope(include_deleted).filter(cls.created_at >= since).count()

    @classmethod
    def count_done_since(cls, since, include_deleted=False):
        return cls._scope(include_deleted).filter(cls.status == DONE_STATUS, cls.updated_at >= since).count()

    @classmethod
    def totals_by_user(cls, include_deleted=False):
        """{user_id: (total, concluídas)} numa única query."""
        query = db.session.query(cls.user_id, func.count(cls.id),
                                 func.sum(case((cls.status == DONE_STATUS, 1), else_=0)))
        if not include_deleted:
            query = query.filter(cls.deleted.is_(False))
        return {user_id: (total, int(done or 0)) for user_id, total, done in query.group_by(cls.user_id).all()}

    @staticmethod
    def completion_rate(done, total):
        return round((done / total) * 100, 2) if total > 0 else 0
