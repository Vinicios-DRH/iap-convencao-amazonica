from src import database
from src.models import Download
from src.services.audit import log_audit
from src.services.portal.uploads import save_upload


def list_downloads():
    return Download.query.order_by(Download.created_at.desc()).all()


def list_active_downloads():
    return Download.query.filter_by(is_active=True).order_by(Download.created_at.desc()).all()


def create_download(form, actor_user_id) -> Download:
    file_key = save_upload(form.file.data, folder="cms/downloads") if form.file.data else None

    download = Download(
        title=form.title.data.strip(),
        description=(form.description.data or "").strip() or None,
        category=(form.category.data or "").strip() or None,
        file_key=file_key,
        external_url=(form.external_url.data or "").strip() or None,
    )
    database.session.add(download)
    log_audit(actor_user_id=actor_user_id, action="cms_download_created", details=f"title={download.title}")
    database.session.commit()
    return download


def update_download(download: Download, form, actor_user_id) -> Download:
    download.title = form.title.data.strip()
    download.description = (form.description.data or "").strip() or None
    download.category = (form.category.data or "").strip() or None
    download.external_url = (form.external_url.data or "").strip() or None
    if form.file.data:
        download.file_key = save_upload(form.file.data, folder="cms/downloads")

    log_audit(actor_user_id=actor_user_id, action="cms_download_updated", details=f"download_id={download.id}")
    database.session.commit()
    return download


def set_download_active(download: Download, is_active: bool, actor_user_id) -> None:
    download.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_download_visibility_changed",
        details=f"download_id={download.id} is_active={is_active}",
    )
    database.session.commit()
