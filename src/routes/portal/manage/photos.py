from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import ValidationError as CSRFValidationError
from flask_wtf.csrf import generate_csrf, validate_csrf

from src import app
from src.decorators import cms_manager_required
from src.forms import PhotoForm
from src.models import Photo
from src.services.portal.photos import (
    create_photo,
    delete_photo,
    find_photo_usages,
    list_photos,
    set_photo_active,
    update_photo,
)


@app.route("/portal/painel/fotos")
@cms_manager_required
def portal_manage_photos():
    return render_template("portal/manage/photos_list.html", photos=list_photos())


@app.route("/portal/painel/fotos/nova", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_photo_new():
    form = PhotoForm()

    if form.validate_on_submit():
        if not form.image.data:
            flash("Selecione uma imagem para enviar.", "warning")
            return render_template("portal/manage/photo_form.html", form=form, photo=None)

        create_photo(form, actor_user_id=current_user.id)
        flash("Foto adicionada com sucesso!", "success")
        return redirect(url_for("portal_manage_photos"))

    return render_template("portal/manage/photo_form.html", form=form, photo=None)


@app.route("/portal/painel/fotos/<int:photo_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_photo_edit(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    form = PhotoForm(obj=photo)

    if form.validate_on_submit():
        update_photo(photo, form, actor_user_id=current_user.id)
        flash("Foto atualizada com sucesso!", "success")
        return redirect(url_for("portal_manage_photos"))

    return render_template("portal/manage/photo_form.html", form=form, photo=photo)


@app.route("/portal/painel/fotos/<int:photo_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_photo_hide(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    set_photo_active(photo, is_active=False, actor_user_id=current_user.id)
    flash("Foto ocultada.", "info")
    return redirect(url_for("portal_manage_photos"))


@app.route("/portal/painel/fotos/<int:photo_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_photo_show(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    set_photo_active(photo, is_active=True, actor_user_id=current_user.id)
    flash("Foto reativada.", "success")
    return redirect(url_for("portal_manage_photos"))


@app.route("/portal/painel/fotos/<int:photo_id>/excluir", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_photo_delete(photo_id):
    photo = Photo.query.get_or_404(photo_id)

    # exclusão de verdade só a partir de uma foto já oculta -- obriga o operador a
    # confirmar em duas etapas antes de mexer em algo sem volta.
    if photo.is_active:
        flash("Oculte a foto antes de excluir definitivamente.", "warning")
        return redirect(url_for("portal_manage_photos"))

    if request.method == "POST":
        try:
            validate_csrf(request.form.get("csrf_token"))
        except CSRFValidationError:
            flash("Sessão expirada, recarregue a página e tente de novo.", "danger")
            return redirect(url_for("portal_manage_photo_delete", photo_id=photo.id))

        try:
            delete_photo(photo, actor_user_id=current_user.id)
        except Exception:
            app.logger.exception("Erro ao excluir a foto %s do bucket.", photo.id)
            flash("Não foi possível excluir a imagem do bucket. Tente novamente.", "danger")
            return redirect(url_for("portal_manage_photos"))

        flash("Imagem excluída definitivamente do bucket.", "success")
        return redirect(url_for("portal_manage_photos"))

    return render_template(
        "portal/manage/photo_confirm_delete.html",
        photo=photo,
        usages=find_photo_usages(photo),
        csrf_token=generate_csrf(),
    )
