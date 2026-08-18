from src import database
from src.models import Photo
from src.services.audit import log_audit
from src.services.portal.uploads import save_image_upload


def list_photos():
    return Photo.query.order_by(Photo.created_at.desc()).all()


def list_active_photos():
    return Photo.query.filter_by(is_active=True).order_by(Photo.created_at.desc()).all()


def track_image(image_key: str, caption: str, album: str | None = None) -> Photo:
    """
    Registra na galeria uma imagem que já foi enviada ao B2 por outro fluxo
    (capa de artigo, imagem inserida no corpo do artigo) — pra ela aparecer
    em /portal/galeria com uma legenda dizendo o que é, sem precisar que o
    gestor cadastre ela de novo manualmente.
    """
    photo = Photo(caption=caption, album=album, image_key=image_key)
    database.session.add(photo)
    database.session.commit()
    return photo


def create_photo(form, actor_user_id) -> Photo:
    image_key = save_image_upload(form.image.data, folder="cms/photos")

    photo = Photo(
        caption=(form.caption.data or "").strip() or None,
        album=(form.album.data or "").strip() or None,
        image_key=image_key,
    )
    database.session.add(photo)
    log_audit(actor_user_id=actor_user_id, action="cms_photo_created", details=f"caption={photo.caption}")
    database.session.commit()
    return photo


def update_photo(photo: Photo, form, actor_user_id) -> Photo:
    photo.caption = (form.caption.data or "").strip() or None
    photo.album = (form.album.data or "").strip() or None
    if form.image.data:
        photo.image_key = save_image_upload(form.image.data, folder="cms/photos")

    log_audit(actor_user_id=actor_user_id, action="cms_photo_updated", details=f"photo_id={photo.id}")
    database.session.commit()
    return photo


def set_photo_active(photo: Photo, is_active: bool, actor_user_id) -> None:
    photo.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_photo_visibility_changed",
        details=f"photo_id={photo.id} is_active={is_active}",
    )
    database.session.commit()
