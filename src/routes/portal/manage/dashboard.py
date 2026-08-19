from flask import render_template

from src import app
from src.decorators import cms_manager_required
from src.models import Author, Download, Ministry, NavLink, Photo, Post


@app.route("/portal/painel")
@cms_manager_required
def portal_painel():
    return render_template(
        "portal/manage/dashboard.html",
        total_posts=Post.query.filter_by(post_type="artigo").count(),
        total_pages=Post.query.filter_by(post_type="pagina").count(),
        total_authors=Author.query.count(),
        total_downloads=Download.query.count(),
        total_photos=Photo.query.count(),
        total_nav_links=NavLink.query.count(),
        total_ministries=Ministry.query.count(),
    )
