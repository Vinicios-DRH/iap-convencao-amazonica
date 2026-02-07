from decimal import ROUND_HALF_UP, Decimal
import os
from datetime import datetime
import uuid
from flask import render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

import qrcode
from io import BytesIO
from src.controllers.pix_emv import build_pix_payload
from src import app, database, get_current_lot_info, split_installments
from src.models import AppSetting, User, Role, Registration, AuditLog
from src.forms import ChangePasswordForm, RegisterAndSignupForm, LoginForm, UploadProofForm, ReviewRegistrationForm
from src.decorators import admin_required, payment_reviewer_required, super_required
from src.controllers.b2_utils import upload_to_b2
import secrets
import string
from sqlalchemy import func

PIX_PADRAO_MSG = (
    "Informamos que todos os pagamentos realizados via Pix — seja em valor integral ou parcelado — "
    "devem conter obrigatoriamente os centavos finalizados em 0,09. "
    "Essa padronização é necessária para a correta identificação do pagamento. Agradecemos a compreensão."
)

CRIANCAS_MSG = "Crianças de até 5 anos não pagam a inscrição, desde que dividam a cama com o responsável."

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

PIX_KEY_CNPJ = "17.739.576/0001-78"
PIX_QR_STATIC = "img/qr_pix.jpeg"  # dentro do /static

# helpers rápidos


def is_pix(reg: Registration) -> bool:
    return (reg.payment_type or "").lower() == "pix"


def can_admin():
    return getattr(current_user, "can_access_admin", False)


def can_review():
    return getattr(current_user, "can_review_payments", False)


def inscricoes_suspensas() -> bool:
    return os.getenv("INSCRICOES_SUSPENSAS", "0") == "1"


def inscricoes_abertas() -> bool:
    return os.getenv("INSCRICOES_ABERTAS", "0") == "1"


def get_setting(key: str, default: str = "") -> str:
    s = AppSetting.query.filter_by(key=key).first()
    return (s.value if s else default) or default


def inscricoes_status() -> str:
    return get_setting("INSCRICOES_STATUS", "embreve").strip().lower()


# ======================= PIX =======================
PIX_KEY = "17739576000178"


@app.route("/pix/qr/<int:n>")
@login_required
def pix_qr_n(n):
    reg = Registration.query.filter_by(user_id=current_user.id).first_or_404()

    if n not in (1, 2, 3):
        abort(400)

    lot = Decimal(reg.lot_value_cents or 18000) / Decimal("100")  # ex: 180.00
    parcela = (lot / Decimal(n)).quantize(Decimal("0.01"),
                                          rounding=ROUND_HALF_UP)

    # regra do seu evento: terminar em ,09
    parcela = Decimal(int(parcela)) + Decimal("0.09")  # 90.09 / 60.09 etc.

    payload = build_pix_payload(
        pix_key=PIX_KEY,
        merchant_name="CONVENCAO AMAZONICA",
        merchant_city="MANAUS",
        amount=float(parcela),  # ou str(parcela) se seu builder aceitar string
        txid=f"{reg.id}-{n}"[:25]
    )
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")


@app.route("/pix/copia-cola/<int:n>")
@login_required
def pix_copia_cola(n):
    reg = Registration.query.filter_by(user_id=current_user.id).first_or_404()

    if n not in (1, 2, 3):
        abort(400)

    from decimal import Decimal, ROUND_HALF_UP
    lot = Decimal(reg.lot_value_cents or 18000) / Decimal("100")
    parcela = (lot / Decimal(n)).quantize(Decimal("0.01"),
                                          rounding=ROUND_HALF_UP)
    parcela = Decimal(int(parcela)) + Decimal("0.09")

    payload = build_pix_payload(
        pix_key=PIX_KEY,
        merchant_name="CONVENCAO AMAZONICA",
        merchant_city="MANAUS",
        amount=float(parcela),
        txid=f"{reg.id}-{n}"[:25]
    )

    return {"payload": payload, "valor": str(parcela)}


# ======================= ROUTES =======================


@app.route("/")
def landing():
    v = (request.args.get("v") or "a").lower()

    allowed = {
        "a": "landing_a.html",
        "b": "landing_b.html",
        "c": "landing_c.html",
        "d": "landing_d.html",
        "e": "landing_e.html",
        "f": "landing_f.html",
    }

    tpl = allowed.get(v, "landing_a.html")
    return render_template(
        tpl,
        pix_msg=PIX_PADRAO_MSG,
        criancas_msg=CRIANCAS_MSG,
        inclui_itens=INCLUI_ITENS,
        contato_pagamento=CONTATO_PAGAMENTO,
        contato_pagamento_texto=CONTATO_PAGAMENTO_TEXTO,
        inscricoes_status=inscricoes_status(),
    )


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    st = inscricoes_status()

    if st == "embreve":
        return render_template("inscricoes_em_breve.html",
                               contato_pagamento=CONTATO_PAGAMENTO,
                               contato_pagamento_texto=CONTATO_PAGAMENTO_TEXTO)

    if st == "suspensas":
        return render_template("inscricoes_suspensas.html",
                               contato_pagamento=CONTATO_PAGAMENTO,
                               contato_pagamento_texto=CONTATO_PAGAMENTO_TEXTO)

    # abertas
    form = RegisterAndSignupForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        # evita duplicar conta
        if User.query.filter_by(email=email).first():
            flash(
                "Já existe uma conta com esse e-mail. Faça login para acompanhar.", "warning")
            return redirect(url_for("login"))

        # cria usuário
        user = User(email=email)
        user.set_password(form.password.data)

        # regra de status inicial
        status = "AGUARDANDO_CONFIRMACAO"
        status_msg = "Aguardando confirmação do pagamento."

        reg = Registration(
            user=user,
            full_name=form.full_name.data.strip(),
            cpf=form.cpf.data.strip(),
            phone=form.phone.data.strip(),
            iap_local=form.iap_local.data.strip(),
            transport=form.transport.data,
            payment_type=form.payment_type.data,
            installments=int(form.installments.data),
            lot_name="1_LOTE",
            lot_value_cents=18000,
            status=status,
            status_message=status_msg,
        )

        database.session.add(user)
        database.session.add(reg)
        database.session.add(
            AuditLog(action="user_signup_and_register", details=f"email={email}"))
        database.session.commit()

        login_user(user)
        flash("Inscrição criada! Agora você pode acompanhar o status no painel.", "success")
        return redirect(url_for("painel"))

    return render_template("inscricao.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("painel"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(form.password.data):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("login.html", form=form)

        login_user(user)

        if getattr(user, "must_change_password", False):
            flash("Por segurança, você precisa definir uma nova senha.", "warning")
            return redirect(url_for("change_password"))
        flash("Bem-vindo!", "success")
        return redirect(url_for("painel"))

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("landing"))


@app.route("/minha-senha", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False

        database.session.add(AuditLog(
            actor_user_id=current_user.id,
            action="user_change_password",
            details=f"user_id={current_user.id}"
        ))
        database.session.commit()

        flash("Senha atualizada com sucesso!", "success")
        return redirect(url_for("painel"))

    return render_template("change_password.html", form=form)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(form.password.data):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("admin/login.html", form=form)

        login_user(user)

        # trava: só entra se tiver acesso ao admin
        if not getattr(user, "can_access_admin", False):
            logout_user()
            flash("Você não tem permissão para acessar o Admin.", "warning")
            return redirect(url_for("login"))

        flash("Acesso administrativo liberado.", "success")
        return redirect(url_for("admin_home"))

    return render_template("admin/login.html", form=form)


@app.route("/painel")
@login_required
def painel():
    reg = current_user.registration  # você já usa 1:1

    total_regs = Registration.query.count()
    lot_info = get_current_lot_info(total_regs)

    # preço "oficial de identificação", sempre terminando em ,09
    price_id = lot_info["price"]  # já vem com .09 se você colocar no env assim
    v1 = price_id
    v2 = split_installments(price_id, 2)[0]  # mesma parcela repetida
    v3 = split_installments(price_id, 3)[0]

    credit_link = "https://link.infinitepay.io/senamarcos/VC1DLTAtUg-7EMh4AJ0qL-180,00"
    return render_template(
        "painel.html",
        reg=reg,
        lot_info=lot_info,
        pix_prices={
            "v1": v1,
            "v2": v2,
            "v3": v3,
        }, credit_link=credit_link
    )


@app.route("/comprovante", methods=["GET", "POST"])
@login_required
def enviar_comprovante():
    reg = Registration.query.filter_by(user_id=current_user.id).first()
    if not reg:
        flash("Você ainda não possui inscrição. Faça sua inscrição primeiro.", "warning")
        return redirect(url_for("inscricao"))

    if not is_pix(reg):
        flash("Envio de comprovante é apenas para pagamento via Pix.", "warning")
        return redirect(url_for("painel"))

    form = UploadProofForm()
    if form.validate_on_submit():
        file = form.proof.data
        ext = os.path.splitext(file.filename or "")[1].lower().replace(".", "")
        safe_ext = ext if ext in ("pdf", "jpg", "jpeg", "png") else "pdf"

        # caminho único no B2
        key = f"comprovantes/{reg.id}/{uuid.uuid4().hex}.{safe_ext}"

        upload_to_b2(filename=key, fileobj=file.stream)
        reg.proof_file_path = key
        reg.proof_uploaded_at = datetime.utcnow()
        reg.status = "AGUARDANDO_CONFIRMACAO"
        reg.status_message = "Comprovante enviado. Aguardando validação do administrador."

        database.session.add(AuditLog(
            actor_user_id=current_user.id,
            action="upload_proof",
            details=f"registration_id={reg.id} key={key}"
        ))
        database.session.commit()

        flash("Comprovante enviado! Agora é só aguardar a confirmação.", "success")
        return redirect(url_for("painel"))

    return render_template("upload_comprovante.html", form=form, reg=reg)


# =======================
# ADMIN
# =======================

@app.route("/admin")
@admin_required
def admin_home():
    # KPIs principais
    total = database.session.query(func.count(Registration.id)).scalar() or 0

    aguardando = (
        database.session.query(func.count(Registration.id))
        .filter(Registration.status == "AGUARDANDO_CONFIRMACAO")
        .scalar()
        or 0
    )

    confirmadas = (
        database.session.query(func.count(Registration.id))
        .filter(Registration.status == "CONFIRMADA")
        .scalar()
        or 0
    )

    negadas = (
        database.session.query(func.count(Registration.id))
        .filter(Registration.status == "NEGADA")
        .scalar()
        or 0
    )

    # Extra: quantas inscrições Pix estão aguardando e já enviaram comprovante
    pendentes_comprovante = (
        database.session.query(func.count(Registration.id))
        .filter(
            Registration.payment_type == "pix",
            Registration.status == "AGUARDANDO_CONFIRMACAO",
            Registration.proof_file_path.isnot(None),
        )
        .scalar()
        or 0
    )

    # Extra: últimas 8 inscrições (para visão rápida)
    ultimas = (
        Registration.query
        .order_by(Registration.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "admin/home.html",
        kpi_total=total,
        kpi_aguardando=aguardando,
        kpi_confirmadas=confirmadas,
        kpi_negadas=negadas,
        kpi_pendentes_comprovante=pendentes_comprovante,
        ultimas=ultimas,
    )


@app.route("/admin/inscricoes")
@payment_reviewer_required
def admin_inscricoes():
    if not can_admin():
        abort(403)

    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()

    query = Registration.query

    if status:
        query = query.filter(Registration.status == status)

    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            (Registration.full_name.ilike(like)) |
            (Registration.email.ilike(like) if hasattr(Registration, "email") else False) |
            (Registration.cpf.ilike(like)) |
            (Registration.phone.ilike(like)) |
            (Registration.iap_local.ilike(like))
        )

    regs = query.order_by(Registration.created_at.desc()).all()
    return render_template("admin/inscricoes.html", regs=regs, status=status, q=q)


@app.route("/admin/inscricoes/<int:reg_id>", methods=["GET", "POST"])
@login_required
def admin_inscricao_detalhe(reg_id):
    if not can_review():
        abort(403)

    reg = Registration.query.get_or_404(reg_id)
    form = ReviewRegistrationForm()

    if form.validate_on_submit():
        decision = form.decision.data  # CONFIRMADA | NEGADA
        note = (form.note.data or "").strip()

        reg.status = decision
        if decision == "CONFIRMADA":
            reg.status_message = "Inscrição confirmada. Seja bem-vindo(a)!"
        else:
            reg.status_message = "Inscrição negada. Entre em contato para ajustes."

        reg.review_note = note if note else None
        reg.reviewed_by_user_id = current_user.id
        reg.reviewed_at = datetime.utcnow()

        database.session.add(AuditLog(
            actor_user_id=current_user.id,
            action="review_registration",
            details=f"registration_id={reg.id} decision={decision}"
        ))
        database.session.commit()

        flash("Decisão salva com sucesso!", "success")
        return redirect(url_for("admin_inscricoes", status=request.args.get("status", "")))

    return render_template("admin/inscricao_detalhe.html", reg=reg, form=form)

# =======================
# SUPER USER - PERMISSÕES
# =======================


def gerar_senha_temporaria(tamanho: int = 10) -> str:
    # senha simples e copiável (letras+numeros). Se quiser mais forte, aumento e boto símbolos.
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


@app.route("/admin/permissoes", methods=["GET", "POST"])
@super_required
def super_permissoes():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.order_by(Role.name.asc()).all()

    if request.method == "POST":
        user_id = int(request.form.get("user_id") or 0)
        # add | remove | reset_password
        action = (request.form.get("action") or "").strip().lower()

        user = User.query.get_or_404(user_id)

        # =========================
        # RESET SENHA
        # =========================
        if action == "reset_password":
            nova_senha = gerar_senha_temporaria(10)
            user.set_password(nova_senha)

            user.must_change_password = True
            user.password_reset_at = datetime.utcnow()

            database.session.add(AuditLog(
                actor_user_id=current_user.id,
                action="super_reset_password",
                details=f"user_id={user_id}"
            ))
            database.session.commit()

            # abre modal no front
            return redirect(url_for("super_permissoes", pw=nova_senha, email=user.email))

        # =========================
        # ADD / REMOVE ROLE
        # =========================
        role_id = int(request.form.get("role_id") or 0)
        role = Role.query.get_or_404(role_id)

        if action == "add" and role not in user.roles:
            user.roles.append(role)
        elif action == "remove" and role in user.roles:
            user.roles.remove(role)

        database.session.add(AuditLog(
            actor_user_id=current_user.id,
            action="super_update_role",
            details=f"user_id={user_id} role_id={role_id} action={action}"
        ))
        database.session.commit()

        flash("Permissões atualizadas.", "success")
        return redirect(url_for("super_permissoes"))

    return render_template("admin/permissoes.html", users=users, roles=roles)


# =======================
# BOOTSTRAP ROLES (rodar 1x)
# =======================
@app.cli.command("seed_roles")
def seed_roles():
    """
    flask seed_roles
    """
    def upsert(name, **kwargs):
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, **kwargs)
            database.session.add(r)
        else:
            for k, v in kwargs.items():
                setattr(r, k, v)

    upsert("SUPER", is_super=True, can_access_admin=True,
           can_review_payments=True)
    upsert("ADMIN", is_super=False, can_access_admin=True,
           can_review_payments=True)
    upsert("REVISOR_PAGAMENTOS", is_super=False,
           can_access_admin=True, can_review_payments=True)
    database.session.commit()
    print("Roles criadas/atualizadas.")


@app.cli.command("make_super")
def make_super():
    """
    Uso:
      flask make_super admin@teste.com
    """
    import sys

    if len(sys.argv) < 3:
        print("Uso: flask make_super email@dominio.com")
        return

    email = sys.argv[2].strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"Usuário não encontrado: {email}")
        return

    role_super = Role.query.filter_by(name="SUPER").first()
    if not role_super:
        print("Role SUPER não existe. Rode: flask seed_roles")
        return

    if role_super not in user.roles:
        user.roles.append(role_super)

    database.session.add(AuditLog(
        actor_user_id=None,
        action="cli_make_super",
        details=f"email={email}"
    ))
    database.session.commit()

    print(f"OK! {email} agora é SUPER.")


def generate_temp_password(length=12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.route("/admin/users/<int:user_id>/reset_password", methods=["POST"])
@super_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)

    temp_pass = generate_temp_password(12)
    user.set_password(temp_pass)
    user.must_change_password = True
    user.password_reset_at = datetime.utcnow()

    database.session.add(AuditLog(
        actor_user_id=current_user.id,
        action="admin_reset_password",
        details=f"user_id={user.id} email={user.email}"
    ))
    database.session.commit()

    # Renderiza uma tela que mostra a senha UMA VEZ
    return render_template("admin/reset_password_result.html", user=user, temp_pass=temp_pass)


@app.route("/admin/config/inscricoes", methods=["GET", "POST"])
@super_required
def admin_config_inscricoes():
    key = "INSCRICOES_STATUS"
    current = get_setting(key, "embreve")

    if request.method == "POST":
        new_status = (request.form.get("status") or "").strip().lower()
        if new_status not in ("abertas", "suspensas", "embreve"):
            flash("Status inválido.", "danger")
            return redirect(url_for("admin_config_inscricoes"))

        s = AppSetting.query.filter_by(key=key).first()
        if not s:
            s = AppSetting(key=key, value=new_status)
            database.session.add(s)
        else:
            s.value = new_status

        database.session.add(AuditLog(
            actor_user_id=current_user.id,
            action="update_inscricoes_status",
            details=f"status={new_status}"
        ))
        database.session.commit()

        flash("Status das inscrições atualizado!", "success")
        return redirect(url_for("admin_config_inscricoes"))

    return render_template("admin/config_inscricoes.html", current=current)
