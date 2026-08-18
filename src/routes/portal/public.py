from flask import abort, render_template, request

from src import app
from src.services.portal.banners import list_active_banners
from src.services.portal.downloads import list_active_downloads
from src.services.portal.photos import list_active_photos
from src.services.portal.ministries import (
    get_active_ministry_by_slug,
    list_active_members,
    list_active_ministries,
    list_active_ministry_social_links,
)
from src.services.portal.posts import (
    get_posts_by_tag_slug,
    get_published_post_by_slug,
    list_posts_by_ministry,
    list_published_posts,
    list_published_posts_paginated,
    list_related_posts,
)
from src.services.portal.sanitizer import html_to_meta_description


@app.route("/portal")
def portal_home():
    posts = list_published_posts(limit=6)
    return render_template(
        "portal/home.html",
        posts=posts,
        downloads=list_active_downloads()[:4],
        photos=list_active_photos()[:6],
        banners=list_active_banners(),
    )


@app.route("/portal/artigos")
def portal_articles():
    page = request.args.get("page", 1, type=int)
    pagination = list_published_posts_paginated(page=page)
    return render_template("portal/articles.html", pagination=pagination, posts=pagination.items)


@app.route("/portal/artigos/<slug>")
def portal_post_detail(slug):
    post = get_published_post_by_slug(slug)
    if not post:
        abort(404)

    related = list_related_posts(post, limit=4)
    exclude_ids = [post.id] + [r.id for r in related]
    recent = list_published_posts(limit=4, exclude_ids=exclude_ids)

    ministry_social_links = list_active_ministry_social_links(post.ministry) if post.ministry else []

    meta_description = html_to_meta_description(
        post.summary or post.body,
        fallback=f"Leia mais sobre {post.title} no portal da Convenção Amazônica IAP.",
    )

    return render_template(
        "portal/post_detail.html",
        post=post,
        related_posts=related,
        recent_posts=recent,
        ministry_social_links=ministry_social_links,
        meta_description=meta_description,
    )


@app.route("/portal/tags/<slug>")
def portal_tag(slug):
    page = request.args.get("page", 1, type=int)
    tag, pagination = get_posts_by_tag_slug(slug, page=page, per_page=12)
    if not tag:
        abort(404)
    return render_template(
        "portal/tag.html",
        tag=tag,
        pagination=pagination,
        posts=pagination.items,
        meta_description=f"Artigos marcados com #{tag.name} no portal da Convenção Amazônica IAP.",
    )


@app.route("/portal/ministerios")
def portal_ministries():
    return render_template("portal/ministries.html", ministries=list_active_ministries())


@app.route("/portal/ministerios/<slug>")
def portal_ministry_detail(slug):
    ministry = get_active_ministry_by_slug(slug)
    if not ministry:
        abort(404)

    meta_description = html_to_meta_description(
        ministry.description,
        fallback=f"Conheça o {ministry.name} da Convenção Amazônica IAP.",
    )

    return render_template(
        "portal/ministry_detail.html",
        ministry=ministry,
        members=list_active_members(ministry),
        social_links=list_active_ministry_social_links(ministry),
        posts=list_posts_by_ministry(ministry, limit=6),
        meta_description=meta_description,
    )


@app.route("/portal/downloads")
def portal_downloads():
    downloads = list_active_downloads()
    return render_template("portal/downloads.html", downloads=downloads)


@app.route("/portal/galeria")
def portal_galeria():
    photos = list_active_photos()
    return render_template("portal/galeria.html", photos=photos)
