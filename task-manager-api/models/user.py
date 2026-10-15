import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.soft_delete import SoftDeleteMixin
from utils.constants import ADMIN_ROLE, DEFAULT_ROLE
from utils.time import utc_now

_LEGACY_MD5 = re.compile(r'^[0-9a-f]{32}$')


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
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if self.has_legacy_password_hash():
            legacy = hashlib.md5(raw_password.encode()).hexdigest()  # só verifica; o login regrava no formato novo
            return hmac.compare_digest(self.password, legacy)
        return check_password_hash(self.password, raw_password)

    def has_legacy_password_hash(self):
        return bool(_LEGACY_MD5.match(self.password or ''))

    def is_admin(self):
        return self.role == ADMIN_ROLE

    @classmethod
    def find_by_email(cls, email):
        """Inclui removidos: o e-mail continua ocupado após o soft delete."""
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_active_by_email(cls, email):
        return cls.not_deleted().filter_by(email=email).first()

    @classmethod
    def list_active(cls):
        return cls.not_deleted().order_by(cls.id).all()

    @classmethod
    def list_all(cls):
        return cls.query.order_by(cls.id).all()
