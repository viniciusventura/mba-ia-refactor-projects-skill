from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from models.soft_delete import SoftDeleteMixin
from utils.constants import CLOSED_TASK_STATUSES, DEFAULT_PRIORITY, DEFAULT_TASK_STATUS
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

    # foreign_keys explícito: tasks também referencia users via deleted_by
    user = db.relationship('User', foreign_keys=[user_id], backref='tasks')
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

    def to_detail_dict(self):
        data = self.to_dict()
        data['overdue'] = self.is_overdue()
        return data

    def to_list_dict(self):
        data = self.to_detail_dict()
        data['user_name'] = self.user.name if self.user else None
        data['category_name'] = self.category.name if self.category else None
        return data

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

    def days_overdue(self, now=None):
        return ((now or utc_now()) - self.due_date).days

    def set_tags(self, tags):
        self.tags = ','.join(tags) if isinstance(tags, list) else tags

    # --- consultas -------------------------------------------------------

    @classmethod
    def list_active_with_relations(cls):
        return cls.not_deleted().options(joinedload(cls.user), joinedload(cls.category)).all()

    @classmethod
    def search(cls, query=None, status=None, priority=None, user_id=None):
        tasks = cls.not_deleted()
        if query:
            tasks = tasks.filter(db.or_(cls.title.like(f'%{query}%'), cls.description.like(f'%{query}%')))
        if status:
            tasks = tasks.filter(cls.status == status)
        if priority is not None:
            tasks = tasks.filter(cls.priority == priority)
        if user_id is not None:
            tasks = tasks.filter(cls.user_id == user_id)
        return tasks.all()

    @classmethod
    def _base(cls, include_deleted):
        return cls.query if include_deleted else cls.not_deleted()

    @classmethod
    def all_tasks(cls, include_deleted=False, user_id=None):
        tasks = cls._base(include_deleted)
        if user_id is not None:
            tasks = tasks.filter_by(user_id=user_id)
        return tasks.order_by(cls.id).all()

    @classmethod
    def count_by_status(cls, include_deleted=False):
        rows = cls._base(include_deleted).with_entities(cls.status, func.count(cls.id)).group_by(cls.status).all()
        return dict(rows)

    @classmethod
    def count_by_priority(cls, include_deleted=False):
        rows = cls._base(include_deleted).with_entities(cls.priority, func.count(cls.id)).group_by(cls.priority).all()
        return dict(rows)

    @classmethod
    def count_by_user(cls, include_deleted=False):
        rows = cls._base(include_deleted).with_entities(cls.user_id, func.count(cls.id)).group_by(cls.user_id).all()
        return dict(rows)

    @classmethod
    def count_done_by_user(cls, include_deleted=False):
        rows = (cls._base(include_deleted).filter(cls.status == 'done')
                .with_entities(cls.user_id, func.count(cls.id)).group_by(cls.user_id).all())
        return dict(rows)

    @classmethod
    def count_by_category(cls):
        rows = cls.not_deleted().with_entities(cls.category_id, func.count(cls.id)).group_by(cls.category_id).all()
        return dict(rows)

    @classmethod
    def count_created_since(cls, since, include_deleted=False):
        return cls._base(include_deleted).filter(cls.created_at >= since).count()

    @classmethod
    def count_completed_since(cls, since, include_deleted=False):
        return cls._base(include_deleted).filter(cls.status == 'done', cls.updated_at >= since).count()

    @classmethod
    def soft_delete_by_user(cls, user_id, deleted_by, when):
        """Cascata lógica: marca as tasks ativas do usuário removido (nada é apagado)."""
        for task in cls.not_deleted().filter_by(user_id=user_id).all():
            task.mark_deleted(deleted_by, when)
