from flask import Flask, flash, jsonify, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import datetime
import os
from urllib.parse import urlparse
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import UnidentifiedImageError
from PIL.Image import DecompressionBombError
from supabase import create_client
from src.controllers.b2_utils import get_b2_file_url
from src.constants import (
    PIX_PADRAO_MSG,
    CRIANCAS_MSG,
    INCLUI_ITENS,
    CONTATO_PAGAMENTO,
    CONTATO_PAGAMENTO_TEXTO,
)
import pytz
from decimal import Decimal, ROUND_FLOOR


load_dotenv()


app = Flask(__name__)
# atrás do proxy do Railway, sem isso toda URL absoluta (canonical, og:url, sitemap)
# sairia como http:// mesmo com o site servido em https:// -- confia em 1 hop de proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.jinja_env.globals['get_b2_file_url'] = get_b2_file_url


def get_social_icon(platform):
    # import local: evita ciclo de import (social_links.py depende de src.models,
    # que só existe depois que este módulo termina de carregar)
    from src.services.portal.social_links import get_icon
    return get_icon(platform)


app.jinja_env.globals['get_social_icon'] = get_social_icon

# Carrega as configurações do .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db" #
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.jinja_env.globals.update(enumerate=enumerate)


SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_DB_URL, SUPABASE_KEY)

# Configuração do diretório de uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB — teto duro; acima disso o pedido nem chega na rota

# Extensões
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'alert-info'

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
        price = LOT2_PRICE
        remaining = LOT1_LIMIT - total_regs
    else:
        lot_name = "2_LOTE"
        price = LOT2_PRICE
        remaining = 0
    return {"lot_name": lot_name, "price": price, "remaining": remaining}

# filtros e helpers para o Jinja
app.jinja_env.filters["money_br"] = lambda v: money_br(Decimal(str(v))) if v is not None else "-"

tz_manaus = pytz.timezone("America/Manaus")


@app.template_filter("fmt_manaus")
def fmt_manaus(dt):
    if not dt:
        return "-"
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(tz_manaus).strftime("%d/%m/%Y %H:%M")


def _active_nav_links():
    # import local: cms_nav_links só existe depois de `flask create_cms_tables`.
    # se a tabela ainda não existir, degrada pra lista vazia em vez de derrubar o site inteiro.
    from src.models import NavLink
    try:
        return (
            NavLink.query
            .filter_by(parent_id=None, is_active=True)
            .order_by(NavLink.order)
            .all()
        )
    except Exception:
        database.session.rollback()
        return []


def _active_social_links():
    from src.models import SocialLink
    try:
        return (
            SocialLink.query
            .filter_by(is_active=True)
            .order_by(SocialLink.order)
            .all()
        )
    except Exception:
        database.session.rollback()
        return []


def _portal_footer_settings():
    from src.services.settings import get_footer_settings
    try:
        return get_footer_settings()
    except Exception:
        database.session.rollback()
        return {"endereco": "", "telefone": ""}


def _active_ministries_for_nav():
    from src.models import Ministry
    try:
        return (
            Ministry.query
            .filter_by(is_active=True)
            .order_by(Ministry.name)
            .all()
        )
    except Exception:
        database.session.rollback()
        return []


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

        # portal / CMS
        "nav_links": _active_nav_links(),
        "social_links": _active_social_links(),
        "footer_settings": _portal_footer_settings(),
        "nav_ministries": _active_ministries_for_nav(),
    }


def _wants_json_error() -> bool:
    # rotas de upload que esperam JSON de volta (editores ricos — Quill, artigo e
    # ministério); todas as outras são formulários normais (foto/autor/capa).
    json_upload_paths = {
        url_for("portal_manage_post_upload_image"),
        url_for("portal_manage_ministry_upload_image"),
    }
    return request.path in json_upload_paths


def _safe_redirect_back(fallback_endpoint: str = "portal_painel"):
    # request.referrer é controlado por quem envia a requisição — só reusa se for
    # do próprio site, senão cai num destino fixo (evita open redirect).
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if not parsed.netloc or parsed.netloc == request.host:
            return redirect(referrer)
    return redirect(url_for(fallback_endpoint))


def _reject_upload(message: str, status: int):
    if _wants_json_error():
        return jsonify({"error": message}), status
    flash(message, "danger")
    return _safe_redirect_back()


@app.errorhandler(413)
def handle_upload_too_large(e):
    limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return _reject_upload(f"Arquivo muito grande. O limite é {limit_mb}MB.", 413)


@app.errorhandler(UnidentifiedImageError)
def handle_invalid_image(e):
    return _reject_upload("Arquivo não é uma imagem válida.", 400)


@app.errorhandler(DecompressionBombError)
def handle_image_decompression_bomb(e):
    return _reject_upload("Imagem com resolução alta demais pra processar.", 400)


from src import routes
from src.routes_coracao import bp_coracao

app.register_blueprint(bp_coracao)
app.supabase = supabase
