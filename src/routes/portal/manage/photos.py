from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import PhotoForm
from src.models import Photo
from src.services.portal.photos import create_photo, list_photos, set_photo_active, update_photo


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
