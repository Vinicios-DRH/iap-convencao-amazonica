from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from src import app, database
from src.forms import ChangePasswordForm, LoginForm
from src.models import User
from src.services.audit import log_audit


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
            return render_template("auth/login.html", form=form)

        login_user(user)

        if getattr(user, "must_change_password", False):
            flash("Por segurança, você precisa definir uma nova senha.", "warning")
            return redirect(url_for("change_password"))

        flash("Bem-vindo!", "success")
        return redirect(url_for("painel"))

    return render_template("auth/login.html", form=form)


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

        log_audit(
            actor_user_id=current_user.id,
            action="user_change_password",
            details=f"user_id={current_user.id}",
        )
        database.session.commit()

        flash("Senha atualizada com sucesso!", "success")
        return redirect(url_for("painel"))

    return render_template("auth/change_password.html", form=form)


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


@app.route("/acesso-restrito", methods=["GET", "POST"])
def acesso_restrito():
    if current_user.is_authenticated and current_user.can_manage_cms:
        return redirect(url_for("portal_painel"))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(form.password.data):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("portal/manage/login.html", form=form)

        login_user(user)

        if not getattr(user, "can_manage_cms", False):
            logout_user()
            flash("Você não tem permissão para acessar a gestão do portal.", "warning")
            return redirect(url_for("login"))

        flash("Acesso liberado.", "success")
        return redirect(url_for("portal_painel"))

    return render_template("portal/manage/login.html", form=form)
