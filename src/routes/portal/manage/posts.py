from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import validate_csrf

from src import app
from src.decorators import cms_manager_required
from src.forms import PostForm
from src.models import Post
from src.services.portal.inline_uploads import upload_inline_image
from src.services.portal.ministries import list_active_ministries
from src.services.portal.posts import create_post, list_posts, set_post_published, update_post
from src.services.portal.tags import tags_to_text

NO_MINISTRY_CHOICE = (0, "— nenhum —")


def _populate_ministry_choices(form):
    form.ministry_id.choices = [NO_MINISTRY_CHOICE] + [
        (m.id, m.name) for m in list_active_ministries()
    ]


@app.route("/portal/painel/artigos")
@cms_manager_required
def portal_manage_posts():
    return render_template("portal/manage/posts_list.html", posts=list_posts())


@app.route("/portal/painel/artigos/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_post_new():
    form = PostForm()
    _populate_ministry_choices(form)

    if form.validate_on_submit():
        create_post(form, created_by_user_id=current_user.id)
        flash("Artigo criado com sucesso!", "success")
        return redirect(url_for("portal_manage_posts"))

    return render_template("portal/manage/post_form.html", form=form, post=None)


@app.route("/portal/painel/artigos/<int:post_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_post_edit(post_id):
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    _populate_ministry_choices(form)

    if request.method == "GET":
        form.tags.data = tags_to_text(post.tags)
        form.ministry_id.data = post.ministry.id if post.ministry else 0

    if form.validate_on_submit():
        update_post(post, form, actor_user_id=current_user.id)
        flash("Artigo atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_posts"))

    return render_template("portal/manage/post_form.html", form=form, post=post)


@app.route("/portal/painel/artigos/upload-imagem", methods=["POST"])
@cms_manager_required
def portal_manage_post_upload_image():
    """Recebe upload de imagem inserida no corpo do artigo pelo editor (Quill),
    comprime, salva no B2 e registra na Galeria — em vez do padrão do Quill de
    embutir a imagem inteira como base64 direto no HTML do artigo."""
    try:
        validate_csrf(request.form.get("csrf_token"))
    except CSRFValidationError:
        return jsonify({"error": "Sessão expirada, recarregue a página e tente de novo."}), 400

    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    # UnidentifiedImageError/DecompressionBombError tratados globalmente
    # (src/__init__.py) — devolvem JSON aqui igual, sem precisar duplicar.
    url = upload_inline_image(
        image,
        request.form.get("description"),
        folder="cms/posts/corpo",
        album="Artigos",
        default_caption="Imagem inserida em artigo",
    )
    return jsonify({"url": url})


@app.route("/portal/painel/artigos/<int:post_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_post_hide(post_id):
    post = Post.query.get_or_404(post_id)
    set_post_published(post, is_published=False, actor_user_id=current_user.id)
    flash("Artigo ocultado.", "info")
    return redirect(url_for("portal_manage_posts"))


@app.route("/portal/painel/artigos/<int:post_id>/publicar", methods=["POST"])
@cms_manager_required
def portal_manage_post_show(post_id):
    post = Post.query.get_or_404(post_id)
    set_post_published(post, is_published=True, actor_user_id=current_user.id)
    flash("Artigo publicado.", "success")
    return redirect(url_for("portal_manage_posts"))
