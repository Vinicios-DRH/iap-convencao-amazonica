from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, BooleanField)
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email, Optional
from src.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    lembrar = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')


class InscricaoForm(FlaskForm):
    nome = StringField('Nome', validators=[
                       DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    iap_local = StringField('IAP Local', validators=[DataRequired()])
    submit = SubmitField('Inscrever-se')

    def validate_email(self, email):
        usuario = User.query.filter_by(email=email.data).first()
        if usuario:
            raise ValidationError(
                'E-mail já cadastrado. Por favor, escolha outro e-mail.')


class FormCriarUsuario(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    cpf = StringField('CPF', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[Optional(), Length(6, 20)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[
                                    Optional(), EqualTo('senha')])
    botao_submit_criar_conta = SubmitField('Salvar')
