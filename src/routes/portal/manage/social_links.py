from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import SocialLinkForm
from src.models import SocialLink
from src.services.portal.social_links import (
    create_social_link,
    list_social_links,
    set_social_link_active,
    update_social_link,
)


@app.route("/portal/painel/redes-sociais")
@cms_manager_required
def portal_manage_social_links():
    return render_template("portal/manage/social_links_list.html", links=list_social_links())


@app.route("/portal/painel/redes-sociais/nova", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_social_link_new():
    form = SocialLinkForm()

    if form.validate_on_submit():
        create_social_link(form, actor_user_id=current_user.id)
        flash("Rede social adicionada com sucesso!", "success")
        return redirect(url_for("portal_manage_social_links"))

    return render_template("portal/manage/social_link_form.html", form=form, link=None)


@app.route("/portal/painel/redes-sociais/<int:link_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_social_link_edit(link_id):
    link = SocialLink.query.get_or_404(link_id)
    form = SocialLinkForm(obj=link)

    if form.validate_on_submit():
        update_social_link(link, form, actor_user_id=current_user.id)
        flash("Rede social atualizada com sucesso!", "success")
        return redirect(url_for("portal_manage_social_links"))

    return render_template("portal/manage/social_link_form.html", form=form, link=link)


@app.route("/portal/painel/redes-sociais/<int:link_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_social_link_hide(link_id):
    link = SocialLink.query.get_or_404(link_id)
    set_social_link_active(link, is_active=False, actor_user_id=current_user.id)
    flash("Rede social ocultada.", "info")
    return redirect(url_for("portal_manage_social_links"))


@app.route("/portal/painel/redes-sociais/<int:link_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_social_link_show(link_id):
    link = SocialLink.query.get_or_404(link_id)
    set_social_link_active(link, is_active=True, actor_user_id=current_user.id)
    flash("Rede social reativada.", "success")
    return redirect(url_for("portal_manage_social_links"))
