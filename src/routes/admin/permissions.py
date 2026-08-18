from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from src import app, database
from src.decorators import super_required
from src.models import Role, User
from src.services.audit import log_audit
from src.services.security import generate_temp_password


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

        if action == "reset_password":
            nova_senha = generate_temp_password(10)
            user.set_password(nova_senha)
            user.must_change_password = True
            user.password_reset_at = datetime.utcnow()

            log_audit(
                actor_user_id=current_user.id,
                action="super_reset_password",
                details=f"user_id={user_id}",
            )
            database.session.commit()

            # abre modal no front
            return redirect(url_for("super_permissoes", pw=nova_senha, email=user.email))

        role_id = int(request.form.get("role_id") or 0)
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
    user = User.query.get_or_404(user_id)

    temp_pass = generate_temp_password(12)
    user.set_password(temp_pass)
    user.must_change_password = True
    user.password_reset_at = datetime.utcnow()

    log_audit(
        actor_user_id=current_user.id,
        action="admin_reset_password",
        details=f"user_id={user.id} email={user.email}",
    )
    database.session.commit()

    # Renderiza uma tela que mostra a senha UMA VEZ
    return render_template("admin/reset_password_result.html", user=user, temp_pass=temp_pass)
