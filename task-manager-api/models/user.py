from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.soft_delete import SoftDeleteMixin
from utils.constants import ADMIN_ROLE, DEFAULT_ROLE
from utils.time import utc_now


class User(SoftDeleteMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        # sem password: o hash nunca sai pela API
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password, pwd)

    def is_admin(self):
        return self.role == ADMIN_ROLE

    @classmethod
    def find_active_by_email(cls, email):
        return cls.not_deleted().filter_by(email=email).first()

    @classmethod
    def find_by_email(cls, email):
        """Inclui removidos: o e-mail de um usuário removido continua reservado."""
        return cls.query.filter_by(email=email).first()

    @classmethod
    def all_users(cls):
        return cls.query.order_by(cls.id).all()
