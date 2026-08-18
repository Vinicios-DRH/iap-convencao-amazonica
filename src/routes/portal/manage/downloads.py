from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from src import app
from src.decorators import cms_manager_required
from src.forms import DownloadForm
from src.models import Download
from src.services.portal.downloads import create_download, list_downloads, set_download_active, update_download


@app.route("/portal/painel/downloads")
@cms_manager_required
def portal_manage_downloads():
    return render_template("portal/manage/downloads_list.html", downloads=list_downloads())


@app.route("/portal/painel/downloads/novo", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_download_new():
    form = DownloadForm()

    if form.validate_on_submit():
        create_download(form, actor_user_id=current_user.id)
        flash("Download criado com sucesso!", "success")
        return redirect(url_for("portal_manage_downloads"))

    return render_template("portal/manage/download_form.html", form=form, download=None)


@app.route("/portal/painel/downloads/<int:download_id>/editar", methods=["GET", "POST"])
@cms_manager_required
def portal_manage_download_edit(download_id):
    download = Download.query.get_or_404(download_id)
    form = DownloadForm(obj=download)

    if form.validate_on_submit():
        update_download(download, form, actor_user_id=current_user.id)
        flash("Download atualizado com sucesso!", "success")
        return redirect(url_for("portal_manage_downloads"))

    return render_template("portal/manage/download_form.html", form=form, download=download)


@app.route("/portal/painel/downloads/<int:download_id>/ocultar", methods=["POST"])
@cms_manager_required
def portal_manage_download_hide(download_id):
    download = Download.query.get_or_404(download_id)
    set_download_active(download, is_active=False, actor_user_id=current_user.id)
    flash("Download ocultado.", "info")
    return redirect(url_for("portal_manage_downloads"))


@app.route("/portal/painel/downloads/<int:download_id>/reativar", methods=["POST"])
@cms_manager_required
def portal_manage_download_show(download_id):
    download = Download.query.get_or_404(download_id)
    set_download_active(download, is_active=True, actor_user_id=current_user.id)
    flash("Download reativado.", "success")
    return redirect(url_for("portal_manage_downloads"))
