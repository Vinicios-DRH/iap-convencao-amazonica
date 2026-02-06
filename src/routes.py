import os
from datetime import datetime
import uuid
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from src import app, database
from src.models import User, Role, Registration, AuditLog
from src.forms import RegisterAndSignupForm, LoginForm, UploadProofForm, ReviewRegistrationForm
from src.decorators import admin_required, payment_reviewer_required, super_required
from src.controllers.b2_utils import upload_to_b2

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


# helpers rápidos
def is_pix(reg: Registration) -> bool:
    return (reg.payment_type or "").lower() == "pix"


def can_admin():
    return getattr(current_user, "can_access_admin", False)


def can_review():
    return getattr(current_user, "can_review_payments", False)


def inscricoes_suspensas() -> bool:
    return os.getenv("INSCRICOES_SUSPENSAS", "0") == "0"


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
    )


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    if inscricoes_suspensas():
        return render_template("inscricoes_suspensas.html")

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
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(form.password.data):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("login.html", form=form)

        login_user(user)
        flash("Bem-vindo!", "success")
        return redirect(url_for("painel"))

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("landing"))


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
    reg = Registration.query.filter_by(user_id=current_user.id).first()
    return render_template("painel.html", reg=reg)


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
    return render_template("admin/home.html")


@app.route("/admin/inscricoes")
@login_required
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


@app.route("/admin/permissoes", methods=["GET", "POST"])
@super_required
def super_permissoes():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.order_by(Role.name.asc()).all()

    if request.method == "POST":
        user_id = int(request.form.get("user_id") or 0)
        role_id = int(request.form.get("role_id") or 0)
        action = request.form.get("action")  # "add" ou "remove"

        user = User.query.get_or_404(user_id)
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
           can_review_payments=False)
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
