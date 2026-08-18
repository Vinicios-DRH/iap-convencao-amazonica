from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from src import app, database
from src.decorators import super_required
from src.models import AppSetting
from src.services.audit import log_audit
from src.services.settings import get_setting

INSCRICOES_STATUS_KEY = "INSCRICOES_STATUS"
VALID_INSCRICOES_STATUSES = ("abertas", "suspensas", "embreve")


@app.route("/admin/config/inscricoes", methods=["GET", "POST"])
@super_required
def admin_config_inscricoes():
    current = get_setting(INSCRICOES_STATUS_KEY, "embreve")

    if request.method == "POST":
        new_status = (request.form.get("status") or "").strip().lower()
        if new_status not in VALID_INSCRICOES_STATUSES:
            flash("Status inválido.", "danger")
            return redirect(url_for("admin_config_inscricoes"))

        setting = AppSetting.query.filter_by(key=INSCRICOES_STATUS_KEY).first()
        if not setting:
            setting = AppSetting(key=INSCRICOES_STATUS_KEY, value=new_status)
            database.session.add(setting)
        else:
            setting.value = new_status

        log_audit(
            actor_user_id=current_user.id,
            action="update_inscricoes_status",
            details=f"status={new_status}",
        )
        database.session.commit()

        flash("Status das inscrições atualizado!", "success")
        return redirect(url_for("admin_config_inscricoes"))

    return render_template("admin/config_inscricoes.html", current=current)
