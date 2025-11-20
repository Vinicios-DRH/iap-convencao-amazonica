from src import database, login_manager
from flask_login import UserMixin
from datetime import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

fuso_am = pytz.timezone("America/Manaus")


def agora_manaus():
    return datetime.now(fuso_am)


class User(UserMixin, database.Model):
    __tablename__ = "users"

    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(120), nullable=False)
    email = database.Column(database.String(120), unique=True, nullable=False)
    senha_hash = database.Column(database.String(255), nullable=False)

    # importante: timezone=True pra armazenar info de fuso
    created_at = database.Column(
        database.DateTime(timezone=True),
        default=agora_manaus
    )

    fichas = database.relationship("FichaPasse", backref="usuario", lazy=True)

    def set_password(self, senha: str):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class FichaPasse(database.Model):
    __tablename__ = "ficha_passe"

    id = database.Column(database.Integer, primary_key=True)

    nome = database.Column(database.String(150), nullable=False)
    endereco = database.Column(database.String(255), nullable=False)
    complemento = database.Column(database.String(150))
    bairro = database.Column(database.String(150))
    telefone = database.Column(database.String(40))
    servico = database.Column(database.String(255))

    ja_conhecia = database.Column(database.Boolean, default=False)
    quer_conhecer_mais = database.Column(database.Boolean, default=False)

    created_at = database.Column(
        database.DateTime(timezone=True),
        default=agora_manaus
    )

    usuario_id = database.Column(
        database.Integer, database.ForeignKey("users.id")
    )
