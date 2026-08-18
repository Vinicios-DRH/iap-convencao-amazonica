from flask import Response, render_template, url_for

from src import app
from src.models import Tag
from src.services.portal.ministries import list_active_ministries
from src.services.portal.posts import list_published_posts


@app.route("/robots.txt")
def robots_txt():
    # bloqueia só o que exige login ou é conta/admin -- todo o resto (portal e as
    # páginas públicas da Convenção Jovem) fica aberto pra indexação.
    lines = [
        "User-agent: *",
        "Disallow: /portal/painel/",
        "Disallow: /admin/",
        "Disallow: /painel",
        "Disallow: /minha-senha",
        "Disallow: /acesso-restrito",
        "Disallow: /login",
        "Disallow: /comprovante",
        "",
        f"Sitemap: {url_for('portal_sitemap', _external=True)}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def portal_sitemap():
    urls = []

    def add(endpoint, lastmod=None, changefreq="weekly", priority="0.5", **kwargs):
        urls.append({
            "loc": url_for(endpoint, _external=True, **kwargs),
            "lastmod": lastmod.date().isoformat() if lastmod else None,
            "changefreq": changefreq,
            "priority": priority,
        })

    add("landing", changefreq="weekly", priority="0.8")
    add("portal_home", changefreq="daily", priority="1.0")
    add("portal_articles", changefreq="daily", priority="0.8")
    add("portal_ministries", priority="0.6")
    add("portal_downloads", priority="0.4")
    add("portal_galeria", priority="0.4")

    for post in list_published_posts():
        add(
            "portal_post_detail", slug=post.slug,
            lastmod=post.updated_at or post.created_at,
            changefreq="monthly", priority="0.7",
        )

    for ministry in list_active_ministries():
        add(
            "portal_ministry_detail", slug=ministry.slug,
            lastmod=ministry.updated_at,
            changefreq="monthly", priority="0.5",
        )

    for tag in Tag.query.all():
        add("portal_tag", slug=tag.slug, changefreq="weekly", priority="0.3")

    xml = render_template("portal/sitemap.xml", urls=urls)
    return Response(xml, mimetype="application/xml")
