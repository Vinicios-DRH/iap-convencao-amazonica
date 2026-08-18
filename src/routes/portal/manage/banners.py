from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import BannerForm
from src.models import Banner
from src.services.portal.banners import create_banner, list_banners, set_banner_active, update_banner


@app.route("/portal/painel/banners")
@cms_manager_required
def portal_manage_banners():
    return render_template("portal/manage/banners_list.html", banners=list_banners())


@app.route("/portal/painel/banners/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_banner_new():
    form = BannerForm()

    if form.validate_on_submit():
        if not form.image.data:
            flash("Selecione uma imagem para enviar.", "warning")
            return render_template("portal/manage/banner_form.html", form=form, banner=None)

        create_banner(form, actor_user_id=current_user.id)
        flash("Banner adicionado com sucesso!", "success")
        return redirect(url_for("portal_manage_banners"))

    return render_template("portal/manage/banner_form.html", form=form, banner=None)


@app.route("/portal/painel/banners/<int:banner_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_banner_edit(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    form = BannerForm(obj=banner)

    if form.validate_on_submit():
        update_banner(banner, form, actor_user_id=current_user.id)
        flash("Banner atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_banners"))

    return render_template("portal/manage/banner_form.html", form=form, banner=banner)


@app.route("/portal/painel/banners/<int:banner_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_banner_hide(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    set_banner_active(banner, is_active=False, actor_user_id=current_user.id)
    flash("Banner ocultado.", "info")
    return redirect(url_for("portal_manage_banners"))


@app.route("/portal/painel/banners/<int:banner_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_banner_show(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    set_banner_active(banner, is_active=True, actor_user_id=current_user.id)
    flash("Banner reativado.", "success")
    return redirect(url_for("portal_manage_banners"))
