from sqlalchemy import or_

from src import database
from src.controllers.b2_utils import delete_from_b2
from src.models import Banner, Ministry, Photo, Post
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


def find_photo_usages(photo: Photo) -> dict:
    """
    Checa se essa imagem ainda está em uso em algum lugar (capa de artigo/ministério,
    banner, ou colada dentro do corpo/descrição rica) -- pra avisar o operador antes
    de excluir de vez, já que apagar do bucket quebraria a exibição nesses lugares.
    """
    key = photo.image_key
    posts = Post.query.filter(or_(Post.cover_image_key == key, Post.body.contains(key))).all()
    ministries = Ministry.query.filter(
        or_(Ministry.cover_image_key == key, Ministry.description.contains(key))
    ).all()
    banners = Banner.query.filter(Banner.image_key == key).all()
    return {"posts": posts, "ministries": ministries, "banners": banners}


def delete_photo(photo: Photo, actor_user_id) -> None:
    """
    Exclusão de verdade: apaga o arquivo do bucket e o registro no banco. Ao
    contrário de ocultar (set_photo_active), isso não tem volta.
    """
    delete_from_b2(photo.image_key)

    log_audit(
        actor_user_id=actor_user_id,
        action="cms_photo_deleted",
        details=f"photo_id={photo.id} image_key={photo.image_key}",
    )
    database.session.delete(photo)
    database.session.commit()
