from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, FileField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_wtf.file import FileAllowed
from src.controllers.validators import validate_cpf


class RegisterAndSignupForm(FlaskForm):
    full_name = StringField("Nome completo", validators=[
                            DataRequired(), Length(min=3, max=150)])
    email = StringField(
        "E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    cpf = StringField("CPF", validators=[
                      DataRequired(), validate_cpf, Length(min=11, max=14)])
    phone = StringField("Telefone", validators=[
                        DataRequired(), Length(min=8, max=20)])
    iap_local = StringField("IAP Local", validators=[
                            DataRequired(), Length(min=2, max=120)])

    transport = SelectField(
        "Transporte",
        choices=[("onibus", "Ônibus"), ("carro", "Carro")],
        validators=[DataRequired()],
    )

    payment_type = SelectField(
        "Forma de pagamento",
        choices=[("pix", "Pix"), ("credito", "Crédito (com taxa)")],
        validators=[DataRequired()],
    )

    installments = SelectField(
        "Parcelas",
        choices=[("1", "À vista (1x)"), ("2", "2x (Fev/Mar)"),
                 ("3", "3x (Fev/Mar/Abr)")],
        validators=[DataRequired()],
    )

    password = PasswordField("Senha", validators=[
        DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField("Confirmar senha", validators=[
        DataRequired(), EqualTo("password")])

    submit = SubmitField("Finalizar inscrição")


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class ChangePasswordForm(FlaskForm):
    new_password = PasswordField("Nova senha", validators=[
                                 DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField("Confirmar nova senha", validators=[
                                     DataRequired(), EqualTo("new_password")])
    submit = SubmitField("Salvar nova senha")


class UploadProofForm(FlaskForm):
    proof = FileField(
        "Comprovante (PDF/JPG/PNG)",
        validators=[DataRequired(), FileAllowed(
            ["pdf", "jpg", "jpeg", "png"], "Envie PDF/JPG/PNG.")],
    )
    submit = SubmitField("Enviar comprovante")


class ReviewRegistrationForm(FlaskForm):
    decision = SelectField(
        "Decisão",
        choices=[("CONFIRMADA", "Confirmar"), ("NEGADA", "Negar")],
        validators=[DataRequired()],
    )
    note = TextAreaField("Observação (opcional)",
                         validators=[Length(max=2000)])
    submit = SubmitField("Salvar")
