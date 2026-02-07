from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import datetime
import os
from supabase import create_client
from src.controllers.b2_utils import get_b2_file_url
import pytz


# Carregar variáveis do .env
load_dotenv()


app = Flask(__name__)
app.jinja_env.globals['get_b2_file_url'] = get_b2_file_url

# Carrega as configurações do .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.jinja_env.globals.update(enumerate=enumerate)


SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_DB_URL, SUPABASE_KEY)

# Configuração do diretório de uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png'}

# Extensões
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'alert-info'

PIX_PADRAO_MSG = (
    "Informamos que todos os pagamentos realizados via Pix — seja em valor integral ou parcelado — "
    "devem conter obrigatoriamente os centavos finalizados em 0,09. Essa padronização é necessária "
    "para a correta identificação do pagamento. Agradecemos a compreensão."
)

CRIANCAS_MSG = "Crianças até 5 anos não pagam, desde que dividam cama com responsável."

INCLUI_ITENS = [
    "Dia 20 — Almoço e jantar",
    "Dia 21 — Café da manhã, almoço e jantar",
    "Dia 22 — Café da manhã",
    "Transporte de ônibus (caso prefira) — Saída de Manaus",
    "Quarto climatizado",
    "Cama",
    "Participação em todas as programações durante a convenção jovem",
    "Momento de lazer",
]

CONTATO_PAGAMENTO = "+55 92 8459-6369"
CONTATO_PAGAMENTO_TEXTO = "Número de contato do pagamento de inscrição"

tz_manaus = pytz.timezone("America/Manaus")


@app.template_filter("fmt_manaus")
def fmt_manaus(dt):
    if not dt:
        return "-"
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(tz_manaus).strftime("%d/%m/%Y %H:%M")


@app.context_processor
def inject_globals():
    return {
        "now": datetime.utcnow,
        "pix_msg": PIX_PADRAO_MSG,
        "criancas_msg": CRIANCAS_MSG,
        "inclui_itens": INCLUI_ITENS,
        "contato_pagamento": CONTATO_PAGAMENTO,
        "contato_pagamento_texto": CONTATO_PAGAMENTO_TEXTO,
    }

from src import routes
app.supabase = supabase
