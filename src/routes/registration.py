from flask import flash, redirect, render_template, url_for
from flask_login import login_required, login_user

from src import app
from src.forms import RegisterAndSignupForm
from src.services.registration import create_registration, email_already_registered
from src.services.settings import inscricoes_status


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    status = inscricoes_status()

    if status == "embreve":
        return render_template("convencao_jovem/registration/inscricoes_em_breve.html")

    if status == "suspensas":
        return render_template("convencao_jovem/registration/inscricoes_suspensas.html")

    form = RegisterAndSignupForm()

    if form.validate_on_submit():
        if form.has_kids_u5.data == "sim" and not (form.kids_u5_names.data or "").strip():
            flash("Informe o nome do(a) filho(a) (5 anos ou menos).", "warning")
            return render_template("convencao_jovem/registration/inscricao.html", form=form)

        email = form.email.data.strip().lower()

        if email_already_registered(email):
            flash("Já existe uma conta com esse e-mail. Faça login para acompanhar.", "warning")
            return redirect(url_for("login"))

        user, _registration = create_registration(form)

        login_user(user)
        flash("Inscrição criada! Agora você pode acompanhar o status no painel.", "success")
        return redirect(url_for("painel"))

    return render_template("convencao_jovem/registration/inscricao.html", form=form)


@app.route("/comprovante")
@login_required
def enviar_comprovante():
    # redireciona pro WhatsApp (se quiser)
    return redirect("https://wa.me/559284596369")
