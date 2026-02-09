
from pathlib import Path
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
from decimal import Decimal, ROUND_FLOOR


# ajusta se seu src estiver em outro nível
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


app = Flask(__name__)
app.jinja_env.globals['get_b2_file_url'] = get_b2_file_url

db_mode = (os.getenv("DB_MODE") or "").lower().strip()

if db_mode == "sqlite":
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

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


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default


def _env_dec(name: str, default: str) -> Decimal:
    try:
        return Decimal(str(os.getenv(name, default)).strip().replace(",", "."))
    except Exception:
        return Decimal(default)


LOT1_LIMIT = _env_int("LOT1_LIMIT", 50)
LOT1_PRICE = _env_dec("LOT1_PRICE", "180.09")   # em reais
LOT2_PRICE = _env_dec("LOT2_PRICE", "200.09")   # em reais
PIX_SUFFIX = _env_dec("PIX_SUFFIX", "0.09")     # em reais (centavos)


def money_br(value: Decimal) -> str:
    # formata 1234.56 -> 1.234,56
    s = f"{value:.2f}"
    inteiro, dec = s.split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"{inteiro},{dec}"


def with_suffix(value: Decimal, suffix: Decimal = PIX_SUFFIX) -> Decimal:
    """
    Força o valor a terminar com PIX_SUFFIX.
    Ex: 180.00 -> 180.09
    """
    inteiro = value.quantize(Decimal("1"), rounding=ROUND_FLOOR)
    return inteiro + suffix


def split_installments(total: Decimal, n: int) -> list[Decimal]:
    """
    Divide em parcelas e força cada parcela a terminar em PIX_SUFFIX.
    """
    n = max(1, int(n or 1))
    base = (total / Decimal(n))
    parcela = with_suffix(base)
    return [parcela for _ in range(n)]


def get_current_lot_info(total_regs: int) -> dict:
    """
    Decide lote com base em quantidade total de inscrições (registros).
    """
    if total_regs < LOT1_LIMIT:
        lot_name = "1_LOTE"
        price = LOT1_PRICE
        remaining = LOT1_LIMIT - total_regs
    else:
        lot_name = "2_LOTE"
        price = LOT2_PRICE
        remaining = 0
    return {"lot_name": lot_name, "price": price, "remaining": remaining}


# filtros e helpers para o Jinja
app.jinja_env.filters["money_br"] = lambda v: money_br(
    Decimal(str(v))) if v is not None else "-"

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

        # novos globais
        "lot1_limit": LOT1_LIMIT,
        "pix_suffix": str(PIX_SUFFIX).replace(".", ","),
    }

from src import routes
app.supabase = supabase
