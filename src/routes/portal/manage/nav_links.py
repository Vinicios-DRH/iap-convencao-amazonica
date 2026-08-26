from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import generate_csrf, validate_csrf

from src import app
from src.decorators import cms_manager_required
from src.forms import NavLinkForm
from src.models import NavLink
from src.services.portal.nav_links import (
    create_dropdown,
    create_nav_link,
    list_parent_options,
    list_top_level_links,
    set_nav_link_active,
    update_nav_link,
)
from src.services.portal.posts import list_pages

NO_PARENT_CHOICE = (0, "— item de topo (sem menu pai) —")
NO_PAGE_CHOICE = (0, "— nenhuma (usar URL manual) —")


def _populate_parent_choices(form, exclude_id=None):
    options = list_parent_options()
    if exclude_id:
        options = [o for o in options if o.id != exclude_id]
    form.parent_id.choices = [NO_PARENT_CHOICE] + [(o.id, o.label) for o in options]


def _populate_page_choices(form):
    form.page_id.choices = [NO_PAGE_CHOICE] + [(p.id, p.title) for p in list_pages()]


@app.route("/portal/painel/menu")
@cms_manager_required
def portal_manage_nav_links():
    return render_template("portal/manage/nav_links_list.html", links=list_top_level_links())


@app.route("/portal/painel/menu/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_nav_link_new():
    form = NavLinkForm()
    _populate_parent_choices(form)
    _populate_page_choices(form)

    if request.method == "GET":
        # link direto de "+ Submenu" na listagem -- já vem com o pai escolhido
        form.parent_id.data = request.args.get("parent_id", 0, type=int)

    if form.validate_on_submit():
        create_nav_link(form, actor_user_id=current_user.id)
        flash("Item de menu criado com sucesso!", "success")
        return redirect(url_for("portal_manage_nav_links"))

    return render_template("portal/manage/nav_link_form.html", form=form, link=None)


@app.route("/portal/painel/menu/novo-dropdown", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_nav_dropdown_new():
    """Cria o item de topo (dropdown) e quantos submenus o operador quiser, tudo numa
    tela só -- em vez de criar o pai, salvar, voltar e criar cada filho separado."""
    pages = list_pages()

    if request.method == "POST":
        try:
            validate_csrf(request.form.get("csrf_token"))
        except CSRFValidationError:
            flash("Sessão expirada, recarregue a página e tente de novo.", "danger")
            return redirect(url_for("portal_manage_nav_dropdown_new"))

        label = (request.form.get("label") or "").strip()
        if not label:
            flash("Dê um nome ao dropdown antes de salvar.", "warning")
            return render_template(
                "portal/manage/nav_dropdown_form.html", pages=pages, csrf_token=generate_csrf(),
                posted=request.form,
            )

        child_labels = request.form.getlist("child_label")
        child_page_ids = request.form.getlist("child_page_id")
        child_urls = request.form.getlist("child_url")
        # ordem = posição da linha no formulário -- ajustável depois pelo editar, se precisar
        children = [
            {
                "label": child_labels[i],
                "page_id": int(child_page_ids[i]) if child_page_ids[i] else None,
                "url": child_urls[i],
                "order": i,
            }
            for i in range(len(child_labels))
        ]

        dropdown = create_dropdown(label, request.form.get("order", 0, type=int), children, actor_user_id=current_user.id)
        n_children = len([c for c in children if c["label"].strip()])
        flash(f'Dropdown "{dropdown.label}" criado com {n_children} submenu(s)!', "success")
        return redirect(url_for("portal_manage_nav_links"))

    return render_template("portal/manage/nav_dropdown_form.html", pages=pages, csrf_token=generate_csrf(), posted=None)


@app.route("/portal/painel/menu/<int:link_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_nav_link_edit(link_id):
    link = NavLink.query.get_or_404(link_id)
    form = NavLinkForm(obj=link)
    _populate_parent_choices(form, exclude_id=link.id)
    _populate_page_choices(form)

    if request.method == "GET":
        form.parent_id.data = link.parent_id or 0
        form.page_id.data = link.page_id or 0

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
