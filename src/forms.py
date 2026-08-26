from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, FileField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, URL

from flask_wtf.file import FileAllowed
from src.controllers.validators import validate_cpf

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
DOWNLOAD_EXTENSIONS = ["pdf", "doc", "docx", "ppt", "pptx", "xls",
                       "xlsx", "zip", "jpg", "jpeg", "png"]


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
        choices=[("1", "À vista (1x)"), ("2", "2x"),
                 ("4", "4x")],
        validators=[DataRequired()],
    )

    password = PasswordField("Senha", validators=[
        DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField("Confirmar senha", validators=[
        DataRequired(), EqualTo("password")])

    age = IntegerField(
        "Idade",
        validators=[Optional(), NumberRange(min=6, max=120)],
    )

    has_kids_u5 = SelectField(
        "Vai levar filhos com 5 anos ou menos?",
        choices=[("nao", "Não"), ("sim", "Sim")],
        validators=[DataRequired()],
        default="nao",
    )

    kids_u5_names = StringField(
        "Nome do(a) filho(a) (5 anos ou menos)",
        validators=[Optional(), Length(max=255)],
    )

    is_church_member = SelectField(
        "É membro da igreja?",
        choices=[("nao", "Não"), ("sim", "Sim")],
        validators=[DataRequired()],
        default="sim",
    )

    agree_no_refund = BooleanField(
        "Concordo que, em caso de desistência, os valores já enviados não serão reembolsados",
        validators=[DataRequired()],
    )

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


# ===================== CMS DO PORTAL =====================

class PostForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(min=3, max=200)])
    summary = TextAreaField("Resumo", validators=[Optional(), Length(max=500)])
    body = TextAreaField("Conteúdo", validators=[DataRequired()])
    category = StringField("Categoria", validators=[Optional(), Length(max=80)])
    tags = StringField(
        "Tags (separadas por vírgula)",
        validators=[Optional(), Length(max=300)],
    )
    ministry_id = SelectField("Ministério (opcional)", coerce=int, validators=[Optional()])
    cover_image = FileField(
        "Imagem de capa (opcional)",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    submit = SubmitField("Salvar")


class PageForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(min=3, max=200)])
    summary = TextAreaField("Resumo (opcional)", validators=[Optional(), Length(max=500)])
    body = TextAreaField("Conteúdo", validators=[DataRequired()])
    cover_image = FileField(
        "Imagem de capa (opcional)",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    submit = SubmitField("Salvar")


class AuthorForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(min=2, max=150)])
    bio = TextAreaField("Biografia (opcional)", validators=[Optional(), Length(max=2000)])
    photo = FileField(
        "Foto (opcional)",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    submit = SubmitField("Salvar")


class DownloadForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField("Descrição (opcional)", validators=[Optional(), Length(max=1000)])
    category = StringField("Categoria (opcional)", validators=[Optional(), Length(max=80)])
    external_url = StringField(
        "Link externo (opcional)",
        validators=[Optional(), Length(max=500), URL(require_tld=True, message="Link inválido.")],
    )
    file = FileField(
        "Arquivo (opcional)",
        validators=[Optional(), FileAllowed(DOWNLOAD_EXTENSIONS, "Formato de arquivo não permitido.")],
    )
    submit = SubmitField("Salvar")


class PhotoForm(FlaskForm):
    caption = StringField("Legenda (opcional)", validators=[Optional(), Length(max=200)])
    album = StringField("Álbum (opcional)", validators=[Optional(), Length(max=80)])
    image = FileField(
        "Imagem",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    submit = SubmitField("Salvar")


class BannerForm(FlaskForm):
    image = FileField(
        "Imagem",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    description = StringField(
        "Descrição (usada como texto alternativo da imagem)",
        validators=[DataRequired(), Length(min=3, max=200)],
    )
    link_url = StringField(
        "Link ao clicar (opcional)",
        validators=[Optional(), Length(max=300), URL(require_tld=True, message="Link inválido.")],
    )
    order = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=999)], default=0)
    submit = SubmitField("Salvar")


class NavLinkForm(FlaskForm):
    label = StringField("Texto do link", validators=[DataRequired(), Length(min=1, max=80)])
    page_id = SelectField("Página vinculada (opcional)", coerce=int, validators=[Optional()])
    url = StringField(
        "URL manual (opcional — ignorada se uma página estiver vinculada acima)",
        validators=[Optional(), Length(max=300)],
    )
    parent_id = SelectField("Menu pai (opcional)", coerce=int, validators=[Optional()])
    order = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=999)], default=0)
    submit = SubmitField("Salvar")


SOCIAL_PLATFORM_CHOICES = [
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("youtube", "YouTube"),
    ("whatsapp", "WhatsApp"),
    ("tiktok", "TikTok"),
    ("x", "X (Twitter)"),
    ("outro", "Outro"),
]


class SocialLinkForm(FlaskForm):
    platform = SelectField("Rede", choices=SOCIAL_PLATFORM_CHOICES, validators=[DataRequired()])
    url = StringField("Link", validators=[DataRequired(), Length(max=300), URL(require_tld=True, message="Link inválido.")])
    order = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=999)], default=0)
    submit = SubmitField("Salvar")


class FooterSettingsForm(FlaskForm):
    endereco = StringField("Endereço da sede", validators=[Optional(), Length(max=255)])
    telefone = StringField("Telefone de contato", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Salvar")


class MinistryForm(FlaskForm):
    name = StringField("Nome do ministério", validators=[DataRequired(), Length(min=3, max=120)])
    description = TextAreaField("Descrição e objetivo", validators=[Optional()])
    cover_image = FileField(
        "Imagem de capa (opcional)",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    submit = SubmitField("Salvar")


class MandateForm(FlaskForm):
    """Reaproveitado tanto pelos mandatos de Ministério quanto da Diretoria — mesma forma,
    só muda o que o service faz com o label (associa a um ministério ou não)."""
    label = StringField("Nome do mandato", validators=[DataRequired(), Length(min=3, max=80)])
    submit = SubmitField("Salvar")


class MandateMemberForm(FlaskForm):
    """Reaproveitado por membro de mandato de Ministério e de membro da Diretoria."""
    name = StringField("Nome", validators=[DataRequired(), Length(min=2, max=150)])
    role = StringField("Função", validators=[DataRequired(), Length(max=80)])
    user_id = SelectField("Vincular a uma conta (opcional)", coerce=int, validators=[Optional()])
    photo = FileField(
        "Foto (opcional)",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Envie uma imagem JPG, PNG ou WEBP.")],
    )
    order = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=999)], default=0)
    submit = SubmitField("Salvar")


class MinistrySocialLinkForm(FlaskForm):
    platform = SelectField("Rede", choices=SOCIAL_PLATFORM_CHOICES, validators=[DataRequired()])
    url = StringField("Link", validators=[DataRequired(), Length(max=300), URL(require_tld=True, message="Link inválido.")])
    order = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=999)], default=0)
    submit = SubmitField("Salvar")
