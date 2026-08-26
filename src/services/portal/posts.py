from datetime import datetime

from src import database
from src.controllers.slugify import gerar_slug
from src.models import Ministry, Post, cms_post_tags
from src.services.audit import log_audit
from src.services.portal.photos import track_image
from src.services.portal.sanitizer import sanitize_body
from src.services.portal.tags import get_or_create_tags
from src.services.portal.uploads import save_image_upload


def _slug_taken(slug: str, ignore_id: int | None) -> bool:
    query = Post.query.filter_by(slug=slug)
    if ignore_id:
        query = query.filter(Post.id != ignore_id)
    return query.first() is not None


def _unique_slug(title: str, ignore_id: int | None = None) -> str:
    base = gerar_slug(title) or "post"
    slug = base
    suffix = 2
    while _slug_taken(slug, ignore_id):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def list_posts():
    return Post.query.filter_by(post_type="artigo").order_by(Post.created_at.desc()).all()


def list_published_posts(limit: int | None = None, exclude_ids: list | None = None):
    # post_type="artigo" (default do modelo) -- exclui páginas institucionais, que usam
    # o mesmo modelo Post mas não são "notícia" (ver list_pages/get_published_page_by_slug).
    query = Post.query.filter_by(is_published=True, post_type="artigo")
    if exclude_ids:
        query = query.filter(Post.id.notin_(exclude_ids))
    query = query.order_by(Post.created_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def list_related_posts(post: Post, limit: int = 4):
    """'Veja também' — outros artigos publicados que compartilham ao menos uma tag."""
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    return (
        Post.query
        .join(cms_post_tags, Post.id == cms_post_tags.c.post_id)
        .filter(cms_post_tags.c.tag_id.in_(tag_ids))
        .filter(Post.id != post.id, Post.is_published.is_(True))
        .distinct()
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )


def list_published_posts_paginated(page: int, per_page: int = 12):
    return (
        Post.query
        .filter_by(is_published=True, post_type="artigo")
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def get_published_post_by_slug(slug: str):
    return Post.query.filter_by(slug=slug, is_published=True, post_type="artigo").first()


def get_posts_by_tag_slug(tag_slug: str, page: int, per_page: int):
    from src.models import Tag

    tag = Tag.query.filter_by(slug=tag_slug).first()
    if not tag:
        return None, None

    pagination = (
        Post.query
        .join(cms_post_tags, Post.id == cms_post_tags.c.post_id)
        .filter(cms_post_tags.c.tag_id == tag.id, Post.is_published.is_(True), Post.post_type == "artigo")
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return tag, pagination


def list_posts_by_ministry(ministry: Ministry, limit: int | None = None):
    query = Post.query.filter(Post.ministries.contains(ministry), Post.is_published.is_(True))
    query = query.order_by(Post.created_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def create_post(form, created_by_user_id) -> Post:
    # o autor é sempre quem está logado — sem seleção manual (ver conversa sobre isso)
    cover_image_key = None
    if form.cover_image.data:
        cover_image_key = save_image_upload(form.cover_image.data, folder="cms/posts")

    title = form.title.data.strip()
    post = Post(
        title=title,
        slug=_unique_slug(title),
        summary=(form.summary.data or "").strip() or None,
        body=sanitize_body(form.body.data),
        category=(form.category.data or "").strip() or None,
        cover_image_key=cover_image_key,
        tags=get_or_create_tags(form.tags.data),
        is_published=True,
        published_at=datetime.utcnow(),
        created_by_user_id=created_by_user_id,
    )
    post.ministry = _resolve_ministry(form.ministry_id.data)
    database.session.add(post)
    log_audit(actor_user_id=created_by_user_id, action="cms_post_created", details=f"title={title}")
    database.session.commit()

    if cover_image_key:
        track_image(cover_image_key, caption=f"Capa: {title}", album="Artigos")

    return post


def _resolve_ministry(ministry_id) -> Ministry | None:
    return Ministry.query.get(ministry_id) if ministry_id else None


def update_post(post: Post, form, actor_user_id) -> Post:
    new_title = form.title.data.strip()
    if new_title != post.title:
        post.slug = _unique_slug(new_title, ignore_id=post.id)
    post.title = new_title
    post.summary = (form.summary.data or "").strip() or None
    post.body = sanitize_body(form.body.data)
    post.category = (form.category.data or "").strip() or None
    post.tags = get_or_create_tags(form.tags.data)
    post.ministry = _resolve_ministry(form.ministry_id.data)

    new_cover_key = None
    if form.cover_image.data:
        new_cover_key = save_image_upload(form.cover_image.data, folder="cms/posts")
        post.cover_image_key = new_cover_key

    log_audit(actor_user_id=actor_user_id, action="cms_post_updated", details=f"post_id={post.id}")
    database.session.commit()

    if new_cover_key:
        track_image(new_cover_key, caption=f"Capa: {post.title}", album="Artigos")

    return post


def set_post_published(post: Post, is_published: bool, actor_user_id) -> None:
    post.is_published = is_published
    if is_published and not post.published_at:
        post.published_at = datetime.utcnow()

    log_audit(
        actor_user_id=actor_user_id,
        action="cms_post_visibility_changed",
        details=f"post_id={post.id} is_published={is_published}",
    )
    database.session.commit()


# ===== páginas institucionais (mesmo modelo Post, post_type="pagina") =====
# Sem autor visível, sem tags, sem ministério -- só título, resumo, conteúdo e capa.

def list_pages():
    return Post.query.filter_by(post_type="pagina").order_by(Post.title).all()


def list_published_pages():
    return Post.query.filter_by(is_published=True, post_type="pagina").order_by(Post.title).all()


def get_published_page_by_slug(slug: str):
    return Post.query.filter_by(slug=slug, is_published=True, post_type="pagina").first()


def create_page(form, created_by_user_id) -> Post:
    cover_image_key = None
    if form.cover_image.data:
        cover_image_key = save_image_upload(form.cover_image.data, folder="cms/pages")

    title = form.title.data.strip()
    page = Post(
        title=title,
        slug=_unique_slug(title),
        summary=(form.summary.data or "").strip() or None,
        body=sanitize_body(form.body.data),
        post_type="pagina",
        cover_image_key=cover_image_key,
        is_published=True,
        published_at=datetime.utcnow(),
        created_by_user_id=created_by_user_id,
    )
    database.session.add(page)
    log_audit(actor_user_id=created_by_user_id, action="cms_page_created", details=f"title={title}")
    database.session.commit()

    if cover_image_key:
        track_image(cover_image_key, caption=f"Capa: {title}", album="Páginas")

    return page


def update_page(page: Post, form, actor_user_id) -> Post:
    new_title = form.title.data.strip()
    if new_title != page.title:
        page.slug = _unique_slug(new_title, ignore_id=page.id)
    page.title = new_title
    page.summary = (form.summary.data or "").strip() or None
    page.body = sanitize_body(form.body.data)

    new_cover_key = None
    if form.cover_image.data:
        new_cover_key = save_image_upload(form.cover_image.data, folder="cms/pages")
        page.cover_image_key = new_cover_key

    log_audit(actor_user_id=actor_user_id, action="cms_page_updated", details=f"post_id={page.id}")
    database.session.commit()

    if new_cover_key:
        track_image(new_cover_key, caption=f"Capa: {page.title}", album="Páginas")

    return page
