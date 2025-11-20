# iap_laranjeiras/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    SelectField,
)
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")
    submit = SubmitField("Entrar")


class FichaPasseForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=150)])
    endereco = StringField("Endereço", validators=[
                           DataRequired(), Length(max=255)])
    complemento = StringField("Complemento")
    bairro = StringField("Bairro")
    telefone = StringField("Telefone", validators=[Length(max=40)])

    servico = SelectField(
        "Qual serviço?",
        choices=[
            (
                "juridico_psicologico",
                "Atendimento jurídico e psicológico voltado especialmente para mulheres e crianças."
            ),
            (
                "programacao_criancas",
                "Programação educativa e recreativa para crianças;"
            ),
            (
                "cidadania_diversos",
                "Serviços de cidadania diversos, conforme a disponibilidade da Secretaria;"
            ),
            (
                "emissao_documentos",
                "Emissão de carteiras de identificação como a CIPcD e a CIPTEA + orientação sobre passes de transporte."
            ),
            (
                "programas_projetos",
                "Programas e projetos: Acesso a financiamento, mobilidade 'Inclusão sobre Rodas' e 'Amazonas Eficiente'."
            ),
            (
                "encaminhamento_trabalho",
                "Encaminhamento para o mercado de trabalho + elaboração de currículos (parceria com Setrab)."
            ),
            (
                "atendimento_especializado",
                "Atendimento especializado: orientação jurídica, psicossocial, averiguação de denúncias e tradução em Libras."
            ),
        ],
        validators=[DataRequired()],
    )

    ja_conhecia = SelectField(
        "Já conhecia a igreja?",
        choices=[("sim", "Sim"), ("nao", "Não")],
        validators=[DataRequired()],
    )

    quer_conhecer_mais = SelectField(
        "Gostaria de conhecer um pouco mais?",
        choices=[("sim", "Sim"), ("nao", "Não")],
        validators=[DataRequired()],
    )

    submit = SubmitField("Salvar ficha")

    # dentro da FichaPasseForm
    @property
    def choices_dict(self):
        return dict(self.servico.choices)
