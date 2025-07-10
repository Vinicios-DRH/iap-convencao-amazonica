from src import database, login_manager
from flask_login import UserMixin
from datetime import datetime
from datetime import datetime
import pytz

def agora_manaus():
    fuso_am = pytz.timezone("America/Manaus")
    return datetime.now(fuso_am)


class FuncaoUser(database.Model):
    __tablename__ = "funcao_user"
    id = database.Column(database.Integer, primary_key=True)
    ocupacao = database.Column(database.String(50), nullable=False)
    user = database.relationship('User', backref='user_funcao')


@login_manager.user_loader
def load_usuario(id_usuario):
    return User.query.get(int(id_usuario))


class User(database.Model, UserMixin):
    __tablename__ = "user"
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(100))
    email = database.Column(database.String(50))
    senha = database.Column(database.String(500))
    funcao_user_id = database.Column(
        database.Integer, database.ForeignKey('funcao_user.id'))
    iap_local = database.Column(database.String(100), nullable=False)
    telefone = database.Column(database.String(20))
    ip_address = database.Column(database.String(45))
    data_criacao = database.Column(
        database.DateTime, default=agora_manaus)
    data_ultimo_acesso = database.Column(
        database.DateTime, default=agora_manaus)

    funcao_user = database.relationship(
        'FuncaoUser', foreign_keys=[funcao_user_id])
    comprovantes_pagamento = database.relationship(
        "ComprovantesPagamento", backref="usuario", lazy=True)


class ComprovantesPagamento(database.Model):
    __tablename__ = "comprovantes_pagamento"
    id = database.Column(database.Integer, primary_key=True)
    id_user = database.Column(
        database.Integer, database.ForeignKey('user.id'))
    arquivo_comprovante = database.Column(database.String(50))
    parcela = database.Column(database.String(20))
    data_envio = database.Column(database.DateTime, default=agora_manaus)
    status = database.Column(database.String(50))
