from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import validate_csrf

from src import app
from src.decorators import cms_manager_required
from src.forms import PageForm
from src.models import Post
from src.services.portal.inline_uploads import upload_inline_image
from src.services.portal.posts import create_page, list_pages, set_post_published, update_page


def _get_page_or_404(page_id) -> Post:
    return Post.query.filter_by(id=page_id, post_type="pagina").first_or_404()


@app.route("/portal/painel/paginas")
@cms_manager_required
def portal_manage_pages():
    return render_template("portal/manage/pages_list.html", pages=list_pages())


@app.route("/portal/painel/paginas/nova", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_page_new():
    form = PageForm()

    if form.validate_on_submit():
        create_page(form, created_by_user_id=current_user.id)
        flash("Página criada com sucesso!", "success")
        return redirect(url_for("portal_manage_pages"))

    return render_template("portal/manage/page_form.html", form=form, page=None)


@app.route("/portal/painel/paginas/<int:page_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_page_edit(page_id):
    page = _get_page_or_404(page_id)
    form = PageForm(obj=page)

    if form.validate_on_submit():
        update_page(page, form, actor_user_id=current_user.id)
        flash("Página atualizada com sucesso!", "success")
        return redirect(url_for("portal_manage_pages"))

    return render_template("portal/manage/page_form.html", form=form, page=page)


@app.route("/portal/painel/paginas/upload-imagem", methods=["POST"])
@cms_manager_required
def portal_manage_page_upload_image():
    """Mesmo papel de portal_manage_post_upload_image, mas pro editor de página
    institucional — pasta e álbum próprios na Galeria."""
    try:
        validate_csrf(request.form.get("csrf_token"))
    except CSRFValidationError:
        return jsonify({"error": "Sessão expirada, recarregue a página e tente de novo."}), 400

    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    url = upload_inline_image(
        image,
        request.form.get("description"),
        folder="cms/pages/corpo",
        album="Páginas",
        default_caption="Imagem inserida em página institucional",
    )
    return jsonify({"url": url})


@app.route("/portal/painel/paginas/<int:page_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_page_hide(page_id):
    page = _get_page_or_404(page_id)
    set_post_published(page, is_published=False, actor_user_id=current_user.id)
    flash("Página ocultada.", "info")
    return redirect(url_for("portal_manage_pages"))


@app.route("/portal/painel/paginas/<int:page_id>/publicar", methods=["POST"])
@cms_manager_required
def portal_manage_page_show(page_id):
    page = _get_page_or_404(page_id)
    set_post_published(page, is_published=True, actor_user_id=current_user.id)
    flash("Página publicada.", "success")
    return redirect(url_for("portal_manage_pages"))
