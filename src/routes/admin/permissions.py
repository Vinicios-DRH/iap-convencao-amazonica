from datetime import datetime

from flask import flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import generate_csrf, validate_csrf
from sqlalchemy import or_

from src import app, database
from src.decorators import super_required
from src.models import Registration, Role, User
from src.services.audit import log_audit
from src.services.security import generate_temp_password


def _executar_reset_senha(usuario: User) -> str:
    """Troca a senha, força a troca no próximo login e registra a auditoria.

    A senha retornada existe somente durante esta requisição -- não é salva em
    texto puro no banco, na URL, no flash ou na sessão.
    """
    senha_temporaria = generate_temp_password(12)

    usuario.set_password(senha_temporaria)
    usuario.must_change_password = True
    usuario.password_reset_at = datetime.utcnow()

    log_audit(
        actor_user_id=current_user.id,
        action="admin_reset_password",
        details=f"user_id={usuario.id} email={usuario.email} force_change=true",
    )
    database.session.commit()

    return senha_temporaria


def _renderizar_resultado_reset(usuario: User, senha_temporaria: str):
    """Renderiza a senha uma vez e impede que a resposta fique em cache."""
    html = render_template(
        "admin/reset_password_result.html",
        usuario=usuario,
        senha_temporaria=senha_temporaria,
    )
    response = make_response(html)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _processar_reset_senha(usuario: User):
    """Executa o reset com tratamento de erro e devolve a resposta correta."""
    if usuario.id == current_user.id:
        flash("Para alterar sua própria senha, utilize a opção Minha Senha.", "warning")
        return redirect(url_for("admin_usuarios"))

    try:
        senha_temporaria = _executar_reset_senha(usuario)
    except Exception:
        database.session.rollback()
        app.logger.exception("Erro ao resetar a senha do usuário %s.", usuario.id)
        flash("Não foi possível resetar a senha. Tente novamente.", "danger")
        return redirect(url_for("admin_usuarios"))

    return _renderizar_resultado_reset(usuario, senha_temporaria)


@app.route("/admin/permissoes", methods=["GET", "POST"])
@super_required
def super_permissoes():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.order_by(Role.name.asc()).all()

    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        # add | remove | reset_password
        action = (request.form.get("action") or "").strip().lower()

        if not user_id:
            flash("Usuário inválido.", "danger")
            return redirect(url_for("super_permissoes"))

        user = User.query.get_or_404(user_id)

        # mantém compatibilidade com o botão de reset da tela antiga
        if action == "reset_password":
            return _processar_reset_senha(user)

        if action not in {"add", "remove"}:
            flash("Ação de permissão inválida.", "danger")
            return redirect(url_for("super_permissoes"))

        role_id = request.form.get("role_id", type=int)
        if not role_id:
            flash("Permissão inválida.", "danger")
            return redirect(url_for("super_permissoes"))

        role = Role.query.get_or_404(role_id)

        if action == "add" and role not in user.roles:
            user.roles.append(role)
        elif action == "remove" and role in user.roles:
            user.roles.remove(role)

        log_audit(
            actor_user_id=current_user.id,
            action="super_update_role",
            details=f"user_id={user_id} role_id={role_id} action={action}",
        )
        database.session.commit()

        flash("Permissões atualizadas.", "success")
        return redirect(url_for("super_permissoes"))

    return render_template("admin/permissoes.html", users=users, roles=roles)


@app.route("/admin/users/<int:user_id>/reset_password", methods=["POST"])
@super_required
def admin_reset_password(user_id):
    usuario = User.query.get_or_404(user_id)
    return _processar_reset_senha(usuario)


# =======================
# SUPER USER - USUÁRIOS E RESET DE SENHA
# =======================

@app.route("/admin/usuarios")
@super_required
def admin_usuarios():
    busca = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = User.query

    if busca:
        termo = f"%{busca}%"
        # o relacionamento entre User e Registration é 1:1 no sistema
        query = (
            query
            .outerjoin(Registration, Registration.user_id == User.id)
            .filter(or_(
                User.email.ilike(termo),
                Registration.full_name.ilike(termo),
                Registration.cpf.ilike(termo),
                Registration.phone.ilike(termo),
            ))
        )

    pagination = (
        query
        .order_by(User.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "admin/usuarios.html",
        usuarios=pagination.items,
        pagination=pagination,
        busca=busca,
        csrf_token=generate_csrf(),
    )


@app.route("/admin/usuarios/<int:user_id>/resetar-senha", methods=["POST"])
@super_required
def admin_resetar_senha(user_id):
    try:
        validate_csrf(request.form.get("csrf_token"))
    except CSRFValidationError:
        flash("Sessão expirada, recarregue a página e tente de novo.", "danger")
        return redirect(url_for("admin_usuarios"))

    usuario = User.query.get_or_404(user_id)
    return _processar_reset_senha(usuario)
