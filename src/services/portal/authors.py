from src import database
from src.models import Author
from src.services.audit import log_audit
from src.services.portal.uploads import save_image_upload


def list_authors():
    return Author.query.order_by(Author.name.asc()).all()


def list_active_authors():
    return Author.query.filter_by(is_active=True).order_by(Author.name.asc()).all()


def create_author(form, actor_user_id) -> Author:
    photo_key = save_image_upload(form.photo.data, folder="cms/authors") if form.photo.data else None

    author = Author(
        name=form.name.data.strip(),
        bio=(form.bio.data or "").strip() or None,
        photo_key=photo_key,
    )
    database.session.add(author)
    log_audit(actor_user_id=actor_user_id, action="cms_author_created", details=f"name={author.name}")
    database.session.commit()
    return author


def update_author(author: Author, form, actor_user_id) -> Author:
    author.name = form.name.data.strip()
    author.bio = (form.bio.data or "").strip() or None
    if form.photo.data:
        author.photo_key = save_image_upload(form.photo.data, folder="cms/authors")

    log_audit(actor_user_id=actor_user_id, action="cms_author_updated", details=f"author_id={author.id}")
    database.session.commit()
    return author


def set_author_active(author: Author, is_active: bool, actor_user_id) -> None:
    author.is_active = is_active
    log_audit(
        actor_user_id=actor_user_id,
        action="cms_author_visibility_changed",
        details=f"author_id={author.id} is_active={is_active}",
    )
    database.session.commit()
