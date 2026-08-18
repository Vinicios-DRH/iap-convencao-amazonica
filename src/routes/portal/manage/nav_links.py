from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import NavLinkForm
from src.models import NavLink
from src.services.portal.nav_links import (
    create_nav_link,
    list_parent_options,
    list_top_level_links,
    set_nav_link_active,
    update_nav_link,
)

NO_PARENT_CHOICE = (0, "— item de topo (sem menu pai) —")


def _populate_parent_choices(form, exclude_id=None):
    options = list_parent_options()
    if exclude_id:
        options = [o for o in options if o.id != exclude_id]
    form.parent_id.choices = [NO_PARENT_CHOICE] + [(o.id, o.label) for o in options]


@app.route("/portal/painel/menu")
@cms_manager_required
def portal_manage_nav_links():
    return render_template("portal/manage/nav_links_list.html", links=list_top_level_links())


@app.route("/portal/painel/menu/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_nav_link_new():
    form = NavLinkForm()
    _populate_parent_choices(form)

    if form.validate_on_submit():
        create_nav_link(form, actor_user_id=current_user.id)
        flash("Item de menu criado com sucesso!", "success")
        return redirect(url_for("portal_manage_nav_links"))

    return render_template("portal/manage/nav_link_form.html", form=form, link=None)


@app.route("/portal/painel/menu/<int:link_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_nav_link_edit(link_id):
    link = NavLink.query.get_or_404(link_id)
    form = NavLinkForm(obj=link)
    _populate_parent_choices(form, exclude_id=link.id)

    if request.method == "GET":
        form.parent_id.data = link.parent_id or 0

    if form.validate_on_submit():
        update_nav_link(link, form, actor_user_id=current_user.id)
        flash("Item de menu atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_nav_links"))

    return render_template("portal/manage/nav_link_form.html", form=form, link=link)


@app.route("/portal/painel/menu/<int:link_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_nav_link_hide(link_id):
    link = NavLink.query.get_or_404(link_id)
    set_nav_link_active(link, is_active=False, actor_user_id=current_user.id)
    flash("Item de menu ocultado.", "info")
    return redirect(url_for("portal_manage_nav_links"))


@app.route("/portal/painel/menu/<int:link_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_nav_link_show(link_id):
    link = NavLink.query.get_or_404(link_id)
    set_nav_link_active(link, is_active=True, actor_user_id=current_user.id)
    flash("Item de menu reativado.", "success")
    return redirect(url_for("portal_manage_nav_links"))
