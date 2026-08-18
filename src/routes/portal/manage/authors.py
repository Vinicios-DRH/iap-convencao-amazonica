from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import AuthorForm
from src.models import Author
from src.services.portal.authors import create_author, list_authors, set_author_active, update_author


@app.route("/portal/painel/autores")
@cms_manager_required
def portal_manage_authors():
    return render_template("portal/manage/authors_list.html", authors=list_authors())


@app.route("/portal/painel/autores/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_author_new():
    form = AuthorForm()

    if form.validate_on_submit():
        create_author(form, actor_user_id=current_user.id)
        flash("Autor criado com sucesso!", "success")
        return redirect(url_for("portal_manage_authors"))

    return render_template("portal/manage/author_form.html", form=form, author=None)


@app.route("/portal/painel/autores/<int:author_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_author_edit(author_id):
    author = Author.query.get_or_404(author_id)
    form = AuthorForm(obj=author)

    if form.validate_on_submit():
        update_author(author, form, actor_user_id=current_user.id)
        flash("Autor atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_authors"))

    return render_template("portal/manage/author_form.html", form=form, author=author)


@app.route("/portal/painel/autores/<int:author_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_author_hide(author_id):
    author = Author.query.get_or_404(author_id)
    set_author_active(author, is_active=False, actor_user_id=current_user.id)
    flash("Autor ocultado.", "info")
    return redirect(url_for("portal_manage_authors"))


@app.route("/portal/painel/autores/<int:author_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_author_show(author_id):
    author = Author.query.get_or_404(author_id)
    set_author_active(author, is_active=True, actor_user_id=current_user.id)
    flash("Autor reativado.", "success")
    return redirect(url_for("portal_manage_authors"))
