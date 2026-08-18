from flask import flash, redirect, render_template, url_for

from src import app
from src.decorators import cms_manager_required
from src.forms import FooterSettingsForm
from src.services.settings import get_footer_settings, update_footer_settings


@app.route("/portal/painel/configuracoes", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_settings():
    current = get_footer_settings()
    form = FooterSettingsForm(data=current)

    if form.validate_on_submit():
        update_footer_settings(endereco=form.endereco.data, telefone=form.telefone.data)
        flash("Configurações do rodapé atualizadas!", "success")
        return redirect(url_for("portal_manage_settings"))

    return render_template("portal/manage/footer_settings.html", form=form)
