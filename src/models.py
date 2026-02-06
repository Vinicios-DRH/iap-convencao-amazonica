from src import database, bcrypt, login_manager
from flask_login import UserMixin
from datetime import datetime
import pytz
from sqlalchemy import UniqueConstraint

fuso_am = pytz.timezone("America/Manaus")


def agora_manaus():
    return datetime.now(fuso_am)


# ====== TABELA ASSOCIATIVA (User <-> Role) ======
user_roles = database.Table(
    "user_roles",
    database.Column("user_id", database.Integer,
                    database.ForeignKey("users.id"), primary_key=True),
    database.Column("role_id", database.Integer,
                    database.ForeignKey("roles.id"), primary_key=True),
)


class Role(database.Model):
    __tablename__ = "roles"
    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(50), unique=True, nullable=False)

    # permissões simples (MVP)
    is_super = database.Column(database.Boolean, default=False)
    can_access_admin = database.Column(database.Boolean, default=False)
    can_review_payments = database.Column(database.Boolean, default=False)

    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Role {self.name}>"


class User(database.Model, UserMixin):
    __tablename__ = "users"
    id = database.Column(database.Integer, primary_key=True)

    email = database.Column(database.String(
        120), unique=True, nullable=False, index=True)
    password_hash = database.Column(database.String(255), nullable=False)

    is_active = database.Column(database.Boolean, default=True)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    roles = database.relationship(
        "Role", secondary=user_roles, backref="users")

    # 1 usuário -> 1 inscrição (você pode mudar pra 1:N depois)
    registration = database.relationship(
        "Registration",
        back_populates="user",
        uselist=False,
        foreign_keys="Registration.user_id"
    )

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(
            password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_super(self) -> bool:
        return any(r.is_super for r in self.roles)

    @property
    def can_access_admin(self) -> bool:
        return self.is_super or any(r.can_access_admin for r in self.roles)

    @property
    def can_review_payments(self) -> bool:
        return self.is_super or any(r.can_review_payments for r in self.roles)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Registration(database.Model):
    __tablename__ = "registrations"

    id = database.Column(database.Integer, primary_key=True)
    user_id = database.Column(database.Integer, database.ForeignKey(
        "users.id"), unique=True, nullable=False)

    full_name = database.Column(database.String(150), nullable=False)
    cpf = database.Column(database.String(
        14), nullable=False)  # pode vir formatado
    phone = database.Column(database.String(20), nullable=False)
    iap_local = database.Column(database.String(120), nullable=False)

    transport = database.Column(database.String(
        20), nullable=False)  # "onibus" | "carro"
    # "pix" | "cartao" | "dinheiro" etc.
    # payment_method = database.Column(database.String(30), nullable=False)

    lot_name = database.Column(database.String(
        40), nullable=False, default="1_LOTE")
    lot_value_cents = database.Column(
        database.Integer, nullable=False, default=18000)

    payment_type = database.Column(database.String(
        20), nullable=False, default="pix")  # pix | credito
    installments = database.Column(
        database.Integer, nullable=False, default=1)        # 1..3

    status = database.Column(database.String(
        30), nullable=False, default="AGUARDANDO_CONFIRMACAO")
    status_message = database.Column(database.String(255), nullable=True)

    # comprovante pix
    proof_file_path = database.Column(database.String(255), nullable=True)
    proof_uploaded_at = database.Column(database.DateTime, nullable=True)

    reviewed_by_user_id = database.Column(
        database.Integer, database.ForeignKey("users.id"), nullable=True)
    reviewed_at = database.Column(database.DateTime, nullable=True)
    review_note = database.Column(database.Text, nullable=True)

    created_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(
        database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("cpf", name="uq_registrations_cpf"),
    )

    user = database.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="registration"
    )

    reviewer = database.relationship(
        "User",
        foreign_keys=[reviewed_by_user_id]
    )

    def __repr__(self):
        return f"<Registration {self.full_name} ({self.status})>"


class AuditLog(database.Model):
    __tablename__ = "audit_logs"
    id = database.Column(database.Integer, primary_key=True)
    actor_user_id = database.Column(
        database.Integer, database.ForeignKey("users.id"), nullable=True)
    action = database.Column(database.String(80), nullable=False)
    details = database.Column(database.Text, nullable=True)
    created_at = database.Column(database.DateTime, default=datetime.utcnow)

    actor = database.relationship("User", foreign_keys=[actor_user_id])
